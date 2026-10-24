import json
import subprocess
import wave
from types import SimpleNamespace

import pytest

from video_subtitleler.services.audio import AudioService, MediaError, run_media


def test_extract_real_pcm(settings, video, tmp_path):
    service = AudioService(settings)
    info = service.probe(video)
    assert (info.width, info.height, info.has_audio) == (640, 360, True)
    wav = service.extract(video, tmp_path / "áudio.wav")
    with wave.open(str(wav)) as source:
        assert (source.getnchannels(), source.getframerate(), source.getsampwidth()) == (1, 16000, 2)
    assert video.is_file()
    with pytest.raises(MediaError):
        service.extract(video, wav)


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("ffmpeg", 1), OSError()])
def test_subprocess_failures_are_domain_errors(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(MediaError):
        run_media(["ffmpeg"], 1)


def test_probe_invalid_and_missing(settings, tmp_path, monkeypatch):
    service = AudioService(settings)
    with pytest.raises(MediaError):
        service.probe(tmp_path / "missing.mp4")
    path = tmp_path / "invalid.mp4"
    path.touch()
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout='{"streams": []}'))
    with pytest.raises(MediaError):
        service.probe(path)


def test_no_audio_and_partial_cleanup(settings, tmp_path, monkeypatch):
    service = AudioService(settings)
    video = tmp_path / "input.mp4"
    video.touch()
    meta = {"format": {"duration": "1", "format_name": "mov,mp4"}, "streams": [{"codec_type": "video", "width": 10, "height": 10}]}
    def fake(args, **kwargs):
        if "-show_format" in args:
            return SimpleNamespace(returncode=0, stdout=json.dumps(meta))
        assert "shell" not in kwargs
        assert "-ac" in args and "16000" in args
        from pathlib import Path
        Path(args[-1]).write_bytes(b"partial")
        return SimpleNamespace(returncode=1, stdout="")
    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(MediaError, match="sem faixa"):
        service.extract(video, tmp_path / "a.wav")
    meta["streams"].append({"codec_type": "audio"})
    with pytest.raises(MediaError):
        service.extract(video, tmp_path / "a.wav")
    assert not (tmp_path / "a.wav").exists()


def test_rotation_metadata_uses_display_dimensions(settings, tmp_path, monkeypatch):
    path = tmp_path / "rotated.mp4"
    path.touch()
    meta = {"format": {"duration": "1", "format_name": "mov,mp4"}, "streams": [{"codec_type": "video", "width": 640, "height": 360, "side_data_list": [{"rotation": -90}]}]}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(meta)))
    info = AudioService(settings).probe(path)
    assert (info.width, info.height) == (360, 640)
