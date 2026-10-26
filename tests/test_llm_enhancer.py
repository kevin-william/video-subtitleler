import asyncio
from types import SimpleNamespace

import pytest

from video_subtitleler.services.llm_enhancer import LLMEnhancer


def client_returning(value):
    async def invoke(messages):
        assert "start" in messages[1][1]
        return value
    return SimpleNamespace(ainvoke=invoke)


@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_success_preserves_identity_and_timing(settings, track, preset):
    client = client_returning({"groups": [{"words": [{"id": 0, "text": "Olá,"}, {"id": 1, "text": "mundo!"}]}]})
    result = LLMEnhancer(settings, client).enhance_with_fallback(track, preset)
    assert result is not track
    assert result.segments[0].text == "Olá, mundo!"
    assert [(w.start, w.end) for w in result.segments[0].words] == [(0.1, 0.7), (0.9, 1.6)]
    assert track.segments[0].text == "Olá mundo"


@pytest.mark.parametrize("raw", [
    {}, {"groups": []},
    {"groups": [{"words": [{"id": 1, "text": "x"}, {"id": 0, "text": "y"}]}]},
    {"groups": [{"words": [{"id": 0, "text": "x", "start": 999}, {"id": 1, "text": "y"}]}]},
    {"groups": [{"words": [{"id": 0, "text": "x"}]}]},
    {"groups": [{"words": [{"id": 0, "text": "new words"}, {"id": 1, "text": "y"}]}]},
])
def test_malformed_identity_or_timestamps_fall_back(settings, track, raw):
    assert LLMEnhancer(settings, client_returning(raw)).enhance_with_fallback(track, "instagram_music") is track


@pytest.mark.parametrize("kind", ["timeout", "quota", "connection"])
def test_provider_failure_logs_no_secrets(settings, track, kind, caplog):
    async def invoke(*args):
        if kind == "timeout":
            await asyncio.sleep(1)
        raise RuntimeError("test-secret-do-not-log")
    bounded = settings.model_copy(update={"llm_timeout": 0.01})
    assert LLMEnhancer(bounded, SimpleNamespace(ainvoke=invoke)).enhance_with_fallback(track, "movie_series") is track
    assert "test-secret" not in caplog.text


def test_unconfigured_provider_fallback(settings, track):
    assert LLMEnhancer(settings).enhance_with_fallback(track, "movie_series") is track


def test_langchain_real_client_against_local_protocol(settings, track):
    pytest.importorskip("langchain_openai")
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from pydantic import SecretStr
    requests = []
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            content = {"groups": [{"words": [{"id": 0, "text": "Olá,"}, {"id": 1, "text": "mundo!"}]}]}
            response = {"id": "test-completion", "object": "chat.completion", "created": 0, "model": "deepseek-chat", "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(content)}, "finish_reason": "stop"}]}
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cfg = type(settings)(_env_file=None, llm_api_key=SecretStr("local-test-only"), llm_base_url=f"http://127.0.0.1:{server.server_port}/v1", llm_timeout=5)
        enhancer = LLMEnhancer(cfg)
        for _ in range(2):
            result = enhancer.enhance_with_fallback(track, "instagram_music")
            assert result is not track
            assert result.segments[0].text == "Olá, mundo!"
        assert len(requests) == 2
        assert requests[0]["model"] == "deepseek-chat"
        assert requests[0]["response_format"] == {"type": "json_object"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
