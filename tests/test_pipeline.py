from types import SimpleNamespace

import pytest

from video_subtitleler.models.schema import SubtitleRequest
from video_subtitleler.services.audio import MediaError, MediaInfo
from video_subtitleler.services.pipeline import Pipeline
from video_subtitleler.storage.job_store import MemoryJobStore


@pytest.mark.parametrize("mode", ["external", "whisper_only", "llm_hybrid"])
@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_mode_matrix_routing_and_cleanup(fake_pipeline, tmp_path, mode, preset):
    request = SubtitleRequest(video_file=tmp_path / "video.mp4", transcription_mode=mode, style_preset=preset, external_subtitle_file=tmp_path / "sub.json" if mode == "external" else None)
    progress = []
    result = fake_pipeline.run(request, on_progress=lambda s: progress.append(s.progress_pct))
    assert result.status == "COMPLETED" and result.progress.progress_pct == 100
    assert progress == sorted(progress)
    if mode == "external":
        assert fake_pipeline.calls == ["render"]
        assert result.progress.steps["transcription"] == "SKIPPED"
    else:
        assert "transcribe" in fake_pipeline.calls
        assert ("enhance" in fake_pipeline.calls) == (mode == "llm_hybrid")
    assert not list(fake_pipeline.settings.work_dir.iterdir())


@pytest.mark.parametrize("stage", ["probe", "extract", "transcribe", "build", "render"])
def test_failure_at_each_stage(fake_pipeline, tmp_path, stage):
    def fail(*a, **k):
        raise MediaError("Teste de falha de mídia.")
    if stage in {"probe", "extract"}:
        setattr(fake_pipeline.audio, stage, fail)
    elif stage == "transcribe":
        fake_pipeline.transcriber.transcribe = fail
    elif stage == "build":
        fake_pipeline.builder.write = fail
    else:
        fake_pipeline.renderer.render = fail
    result = fake_pipeline.run(SubtitleRequest(video_file=tmp_path / "video.mp4"))
    assert result.status == "FAILED"
    assert result.progress.progress_pct < 100
    assert "Teste de falha" in result.progress.error
    if fake_pipeline.settings.work_dir.exists():
        assert not list(fake_pipeline.settings.work_dir.iterdir())


@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_real_external_pipeline(settings, video, track, tmp_path, preset):
    sub = tmp_path / "sub.json"
    sub.write_text(track.model_dump_json(), encoding="utf-8")
    pipeline = Pipeline(settings, MemoryJobStore())
    result = pipeline.run(SubtitleRequest(video_file=video, external_subtitle_file=sub, transcription_mode="external", style_preset=preset))
    assert result.status == "COMPLETED", result.progress.error
    assert result.output_path.is_file()
    assert not list(settings.work_dir.iterdir())


def test_distinct_jobs_and_output_paths(fake_pipeline, tmp_path):
    request = SubtitleRequest(video_file=tmp_path / "video.mp4")
    first, second = fake_pipeline.run(request), fake_pipeline.run(request)
    assert first.job_id != second.job_id
    assert first.output_path != second.output_path
