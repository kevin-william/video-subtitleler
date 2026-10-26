from fastapi.testclient import TestClient
from pydantic import SecretStr

from video_subtitleler.api.app import create_app


def test_static_shell_and_private_paths(settings, tmp_path):
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        for asset, content_type in [("app.js", "javascript"), ("style.css", "css")]:
            response = client.get("/static/" + asset)
            assert response.status_code == 200
            assert content_type in response.headers["content-type"]
        for path in ["/static/missing.js", "/static/.env", "/.env", "/work/jobs.sqlite3"]:
            assert client.get(path).status_code == 404
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
    assert app.state.pipeline is None
    assert not settings.work_dir.exists()


def test_config_is_public_allowlist_and_does_not_load_pipeline(settings):
    settings = settings.model_copy(update={"max_upload_bytes": 12345, "llm_api_key": SecretStr("never-public")})
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/v1/ui-config")
        assert response.json() == {"max_upload_bytes": 12345}
        assert "never-public" not in response.text
    assert app.state.pipeline is None
    assert not settings.database_path.exists()


def test_invalid_lazy_config_returns_safe_error(monkeypatch):
    from video_subtitleler.api import ui
    from video_subtitleler.config import Settings

    def invalid_settings():
        return Settings(_env_file=None, max_upload_bytes=-1)

    monkeypatch.setattr(ui, "Settings", invalid_settings)
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ui-config")
        assert response.status_code == 503
        assert "max_upload_bytes" not in response.text
