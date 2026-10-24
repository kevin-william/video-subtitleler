from typer.testing import CliRunner

from video_subtitleler.cli import main

runner = CliRunner()


def test_help_has_no_model_dependency():
    result = runner.invoke(main.app, ["--help"])
    assert result.exit_code == 0
    assert "process" in result.output


def test_cli_success(fake_pipeline, tmp_path, monkeypatch):
    video = tmp_path / "v.mp4"
    video.touch()
    monkeypatch.setattr(main, "make_pipeline", lambda: fake_pipeline)
    result = runner.invoke(main.app, ["process", str(video), "--style", "instagram_music", "--custom-style", '{"active_color":"#FFD700"}'])
    assert result.exit_code == 0, result.output
    assert "Vídeo legendado" in result.output


def test_cli_invalid_and_missing_input(tmp_path):
    assert runner.invoke(main.app, ["process", str(tmp_path / "missing.mp4")]).exit_code == 2
    video = tmp_path / "v.mp4"
    video.touch()
    assert runner.invoke(main.app, ["process", str(video), "--transcription-mode", "external"]).exit_code == 2
    assert runner.invoke(main.app, ["process", str(video), "--custom-style", "invalid"]).exit_code == 2


def test_cli_failure_has_nonzero_exit(fake_pipeline, tmp_path, monkeypatch):
    from video_subtitleler.services.audio import MediaError
    video = tmp_path / "v.mp4"
    video.touch()
    def fail(*args, **kwargs):
        raise MediaError("Falha de teste.")
    fake_pipeline.audio.probe = fail
    monkeypatch.setattr(main, "make_pipeline", lambda: fake_pipeline)
    result = runner.invoke(main.app, ["process", str(video)])
    assert result.exit_code == 1
    assert "Falha de teste" in result.output


def test_real_cli_external(settings, video, track, tmp_path, monkeypatch):
    from video_subtitleler.services.pipeline import Pipeline
    from video_subtitleler.storage.job_store import MemoryJobStore
    sub = tmp_path / "sub.json"
    sub.write_text(track.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(main, "make_pipeline", lambda: Pipeline(settings, MemoryJobStore()))
    out = tmp_path / "cli-result.mp4"
    result = runner.invoke(main.app, ["process", str(video), "--transcription-mode", "external", "--external-subtitle", str(sub), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert out.is_file()
