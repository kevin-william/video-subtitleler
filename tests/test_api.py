from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from video_subtitleler.api.app import create_app
from video_subtitleler.api import routes
from video_subtitleler.models.schema import JobProgress
from video_subtitleler.services.pipeline import Pipeline
from video_subtitleler.storage.job_store import MemoryJobStore


@pytest.fixture
def client(fake_pipeline):
    with TestClient(create_app(pipeline=fake_pipeline)) as client:
        yield client


def generate(client, **data):
    return client.post("/api/v1/subtitles/generate", files={"video_file": ("../input.mp4", b"fake-test-mp4", "video/mp4")}, data=data)


def test_root_opens_web_interface(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Estúdio de legendas" in response.text


def test_api_cycle_and_download(client, fake_pipeline):
    response = generate(client)
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "QUEUED"
    job_id = response.json()["job_id"]
    state = client.get(f"/api/v1/jobs/{job_id}")
    assert state.json()["status"] == "COMPLETED"
    assert "output_path" not in state.json()
    download = client.get(f"/api/v1/jobs/{job_id}/download")
    assert download.status_code == 200 and download.content == b"rendered-test-video"
    assert download.headers["content-type"] == "video/mp4"
    assert not list(fake_pipeline.settings.work_dir.iterdir())


def test_queued_state_before_background_execution(client, fake_pipeline, monkeypatch):
    pending = []
    monkeypatch.setattr(routes, "execute_job", lambda *args: pending.append(args))
    response = generate(client)
    job_id = response.json()["job_id"]
    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "QUEUED"
    assert client.get(f"/api/v1/jobs/{job_id}/download").status_code == 409
    pipeline, request, ident, temporary = pending.pop()
    try:
        pipeline.run(request, ident)
    finally:
        temporary.cleanup()
    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "COMPLETED"


@pytest.mark.parametrize("data", [{"transcription_mode": "external"}, {"custom_style": "invalid"}, {"custom_style": '{"font_size":0}'}, {"style_preset": "invalid"}, {"language": "bad-language"}])
def test_invalid_fields(client, data):
    assert generate(client, **data).status_code == 422


def test_upload_errors_and_unknown_jobs(client, fake_pipeline):
    assert client.post("/api/v1/subtitles/generate").status_code == 422
    assert client.post("/api/v1/subtitles/generate", files={"video_file": ("input.exe", b"fake")}).status_code == 422
    assert client.post("/api/v1/subtitles/generate", files={"video_file": ("input.mp4", b"")}).status_code == 422
    fake_pipeline.settings = fake_pipeline.settings.model_copy(update={"max_upload_bytes": 2})
    assert generate(client).status_code == 413
    assert client.get(f"/api/v1/jobs/{uuid4()}").status_code == 404


def test_failed_and_missing_output(client, fake_pipeline, tmp_path):
    job = fake_pipeline.store.create()
    fake_pipeline.store.update(JobProgress(job_id=job.job_id, status="FAILED", error="falha"))
    assert client.get(f"/api/v1/jobs/{job.job_id}").json()["status"] == "FAILED"
    assert client.get(f"/api/v1/jobs/{job.job_id}/download").status_code == 409
    another = fake_pipeline.store.create()
    fake_pipeline.store.update(JobProgress(job_id=another.job_id, status="PROCESSING"))
    fake_pipeline.store.update(JobProgress(job_id=another.job_id, status="COMPLETED", progress_pct=100), tmp_path / "missing.mp4")
    assert client.get(f"/api/v1/jobs/{another.job_id}/download").status_code == 404


def test_background_failure_is_reported_and_upload_cleaned(client, fake_pipeline):
    from video_subtitleler.services.audio import MediaError
    def fail(*args, **kwargs):
        raise MediaError("Falha de teste na renderização.")
    fake_pipeline.renderer.render = fail
    response = generate(client)
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    state = client.get(f"/api/v1/jobs/{job_id}").json()
    assert state["status"] == "FAILED"
    assert state["steps"]["burning_subtitles"] == "FAILED"
    assert not list(fake_pipeline.settings.work_dir.iterdir())


def test_real_invalid_content_and_unaligned_karaoke(settings, video):
    pipeline = Pipeline(settings, MemoryJobStore())
    with TestClient(create_app(pipeline=pipeline)) as client:
        response = client.post("/api/v1/subtitles/generate", files={"video_file": ("invalid.mp4", b"not-a-video")})
        assert response.status_code == 422
        response = client.post("/api/v1/subtitles/generate", files={"video_file": ("input.mp4", video.read_bytes()), "external_subtitle_file": ("sub.srt", b"1\n00:00:00,000 --> 00:00:01,000\nHello\n")}, data={"transcription_mode": "external", "style_preset": "instagram_music"})
        assert response.status_code == 422
        assert not list(settings.work_dir.iterdir())


@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_real_api_external(settings, video, track, preset):
    pipeline = Pipeline(settings, MemoryJobStore())
    with TestClient(create_app(pipeline=pipeline)) as client:
        response = client.post("/api/v1/subtitles/generate", files={"video_file": ("input.mp4", video.read_bytes(), "video/mp4"), "external_subtitle_file": ("sub.json", track.model_dump_json().encode(), "application/json")}, data={"transcription_mode": "external", "style_preset": preset})
        assert response.status_code == 202, response.text
        job_id = response.json()["job_id"]
        assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "COMPLETED"
        result = client.get(f"/api/v1/jobs/{job_id}/download")
        assert result.status_code == 200 and len(result.content) > 1000
        assert client.get("/docs").status_code == 200
