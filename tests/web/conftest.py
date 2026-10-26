"""Navegador contra servidor isolado, sem usar a chave/serviço pessoal."""
import socket
import threading
import time

import pytest

pytest.importorskip("playwright.sync_api", reason="Instale o extra web-test para testes de navegador")

from video_subtitleler.api.app import create_app


@pytest.fixture
def serve_app():
    import uvicorn
    servers = []

    def start(app):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        servers.append((server, thread, sock))
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Servidor de teste não iniciou")
            time.sleep(0.01)
        return f"http://127.0.0.1:{port}"

    yield start
    for server, thread, sock in servers:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive(), "Servidor de teste não encerrou"


@pytest.fixture
def web_url(settings, serve_app):
    return serve_app(create_app(settings))


@pytest.fixture
def fake_web_url(fake_pipeline, serve_app):
    return serve_app(create_app(pipeline=fake_pipeline))


@pytest.fixture
def real_web_url(settings, serve_app):
    from video_subtitleler.services.pipeline import Pipeline
    from video_subtitleler.storage.job_store import MemoryJobStore
    return serve_app(create_app(pipeline=Pipeline(settings, MemoryJobStore())))


@pytest.fixture
def mock_job(page):
    """Control UI states; deliberately does not claim real transcription."""
    def configure(status="COMPLETED", progress=100, error=None):
        job_id = "00000000-0000-4000-8000-000000000001"
        submitted = []

        def post(route):
            submitted.append(route.request.post_data_buffer)
            route.fulfill(status=202, json={"job_id": job_id, "status": "QUEUED"})

        page.route("**/api/v1/subtitles/generate", post)
        page.route(f"**/api/v1/jobs/{job_id}", lambda route: route.fulfill(json={
            "job_id": job_id, "status": status, "progress_pct": progress,
            "current_step": "burning_subtitles", "steps": {key: "COMPLETED" for key in ["extract_audio", "transcription", "llm_enhancement", "generate_ass", "burning_subtitles"]}, "error": error,
        }))
        return submitted, job_id
    return configure
