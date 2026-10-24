import shutil
from pathlib import Path

import pytest

from video_subtitleler.config import Settings
from video_subtitleler.models.subtitles import Segment, SubtitleTrack, Word
from video_subtitleler.services.audio import run_media


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, work_dir=tmp_path / "work", output_dir=tmp_path / "output", database_path=tmp_path / "jobs.sqlite3", media_timeout=30)


@pytest.fixture
def track():
    return SubtitleTrack(language="pt", segments=(Segment(text="Olá mundo", start=0.1, end=1.6, words=(Word(text="Olá", start=0.1, end=0.7), Word(text="mundo", start=0.9, end=1.6))),))


@pytest.fixture
def video(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/FFprobe não disponíveis")
    path = tmp_path / "vídeo com espaço 'teste'.mp4"
    run_media(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=navy:s=640x360:d=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], 30)
    return path

from types import SimpleNamespace
from video_subtitleler.services.audio import MediaInfo
from video_subtitleler.services.pipeline import Pipeline
from video_subtitleler.storage.job_store import MemoryJobStore

@pytest.fixture
def fake_pipeline(settings, track):
    calls = []
    def extract(video, output):
        calls.append("extract")
        output.write_bytes(b"wav")
        return output
    def transcribe(audio, language):
        calls.append("transcribe")
        return track
    def enhance(source, preset):
        calls.append("enhance")
        return source
    def render(video, ass, output):
        calls.append("render")
        assert ass.is_file()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"rendered-test-video")
        return output
    pipeline = Pipeline(settings, MemoryJobStore(), audio=SimpleNamespace(probe=lambda v: MediaInfo(2, 640, 360, True), extract=extract), transcriber=SimpleNamespace(transcribe=transcribe), enhancer=SimpleNamespace(enhance_with_fallback=enhance), renderer=SimpleNamespace(render=render), external_loader=lambda _: track)
    pipeline.calls = calls
    return pipeline


