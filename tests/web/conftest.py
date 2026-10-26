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
