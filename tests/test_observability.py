import io
import json
import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from video_subtitleler.api.app import create_app
from video_subtitleler.config import Settings
from video_subtitleler.models.schema import StylePreset, SubtitleRequest, TranscriptionMode
from video_subtitleler.observability import (
    JobContextFilter,
    MetricsCollector,
    check_health,
    configure_logging,
    get_current_job_id,
    get_logger,
    job_context,
    metrics,
)
from video_subtitleler.storage.job_store import MemoryJobStore


def test_job_context_management():
    assert get_current_job_id() is None
    job_id_1 = uuid4()
    job_id_2 = uuid4()

    with job_context(job_id_1):
        assert get_current_job_id() == str(job_id_1)
        with job_context(job_id_2):
            assert get_current_job_id() == str(job_id_2)
        assert get_current_job_id() == str(job_id_1)

    assert get_current_job_id() is None


def test_logging_formatter_and_filter():
    stream = io.StringIO()
    configure_logging(level=logging.INFO, stream=stream, json_format=False)
    logger = get_logger("video_subtitleler.test")

    logger.info("Mensagem sem job")
    test_id = uuid4()
    with job_context(test_id):
        logger.info("Mensagem com job")

    output = stream.getvalue()
    assert "[job_id=-] Mensagem sem job" in output
    assert f"[job_id={test_id}] Mensagem com job" in output


def test_json_logging_format():
    stream = io.StringIO()
    configure_logging(level=logging.INFO, stream=stream, json_format=True)
    logger = get_logger("video_subtitleler.test.json")

    test_id = uuid4()
    with job_context(test_id):
        logger.info("Log estruturado em JSON")

    line = stream.getvalue().strip()
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["message"] == "Log estruturado em JSON"
    assert data["job_id"] == str(test_id)
    assert "timestamp" in data


def test_metrics_collector():
    collector = MetricsCollector()
    collector.job_started()
    assert collector.as_dict()["jobs"]["active"] == 1

    collector.record_job(status="COMPLETED", mode="whisper_only", preset="movie_series", duration=12.5)
    collector.record_job(status="COMPLETED", mode="whisper_only", preset="movie_series", duration=7.5)
    collector.job_finished()
    assert collector.as_dict()["jobs"]["active"] == 0

    collector.record_step(step="extract_audio", status="COMPLETED", duration=1.2)
    collector.record_step(step="transcription", status="COMPLETED", duration=5.8)
    collector.record_http_request(method="POST", path="/api/v1/subtitles/generate", status=202, duration=0.05)

    data = collector.as_dict()
    assert data["jobs"]["total"][0]["count"] == 2
    assert data["jobs"]["durations"]["COMPLETED"]["count"] == 2
    assert data["jobs"]["durations"]["COMPLETED"]["avg"] == 10.0
    assert data["jobs"]["durations"]["COMPLETED"]["min"] == 7.5
    assert data["jobs"]["durations"]["COMPLETED"]["max"] == 12.5

    prom = collector.to_prometheus_text()
    assert "video_subtitles_jobs_active 0" in prom
    assert 'video_subtitles_jobs_total{mode="whisper_only",preset="movie_series",status="COMPLETED"} 2' in prom
    assert 'video_subtitles_step_duration_seconds_count{step="extract_audio"} 1' in prom
    assert 'video_subtitles_http_requests_total{method="POST",path="/api/v1/subtitles/generate",status="202"} 1' in prom

    collector.reset()
    assert collector.as_dict()["jobs"]["active"] == 0
    assert not collector.as_dict()["jobs"]["total"]


def test_health_check_ok(tmp_path):
    settings = Settings(
        _env_file=None,
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "output",
        database_path=tmp_path / "jobs.sqlite3",
    )
    result = check_health(settings)
    assert result["status"] in ("healthy", "degraded")
    assert result["http_code"] == 200
    assert result["checks"]["database"]["status"] == "ok"
    assert "free_gb" in result["checks"]["disk"]
    assert "whisper" in result["checks"]
    assert "llm" in result["checks"]


def test_health_check_memory_store(tmp_path):
    settings = Settings(
        _env_file=None,
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "output",
        database_path=tmp_path / "jobs.sqlite3",
    )
    store = MemoryJobStore()
    result = check_health(settings, store)
    assert result["checks"]["database"]["status"] == "ok"


def test_api_observability_endpoints(fake_pipeline):
    metrics.reset()
    app = create_app(pipeline=fake_pipeline)
    with TestClient(app) as client:
        # 1. Health endpoints
        resp_z = client.get("/healthz")
        assert resp_z.status_code == 200
        assert resp_z.json() == {"status": "ok"}

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert "status" in resp_health.json()

        resp_api_health = client.get("/api/v1/health")
        assert resp_api_health.status_code == 200
        assert "checks" in resp_api_health.json()

        # 2. Metrics endpoints
        resp_prom = client.get("/metrics")
        assert resp_prom.status_code == 200
        assert "text/plain" in resp_prom.headers["content-type"]
        assert "video_subtitles_jobs_active" in resp_prom.text

        resp_json_metrics = client.get("/api/v1/metrics")
        assert resp_json_metrics.status_code == 200
        assert "jobs" in resp_json_metrics.json()

        # 3. HTTP middleware tracking
        # The requests above should already have been recorded in metrics
        data = client.get("/api/v1/metrics").json()
        assert len(data["http"]["requests_total"]) > 0


def test_pipeline_records_observability_metrics(fake_pipeline, tmp_path):
    metrics.reset()
    input_video = tmp_path / "video.mp4"
    input_video.write_bytes(b"dummy")

    req = SubtitleRequest(
        video_file=input_video,
        transcription_mode=TranscriptionMode.WHISPER_ONLY,
        style_preset=StylePreset.MOVIE_SERIES,
    )

    result = fake_pipeline.run(req)
    assert result.status == "COMPLETED"

    data = metrics.as_dict()
    assert data["jobs"]["active"] == 0
    assert len(data["jobs"]["total"]) == 1
    assert data["jobs"]["total"][0]["status"] == "COMPLETED"
    assert data["jobs"]["durations"]["COMPLETED"]["count"] == 1
    assert len(data["steps"]["transitions"]) > 0
