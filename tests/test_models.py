from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from video_subtitleler.models.schema import (
    CustomStyle, Job, JobAccepted, JobProgress, JobStatus, SubtitleRequest,
)
from video_subtitleler.models.subtitles import Segment, SubtitleTrack, Word


def test_track_roundtrip_preserves_words_and_times():
    track = SubtitleTrack(language="pt", segments=(Segment(
        text="Olá mundo", start=0, end=1.5,
        words=(Word(text="Olá", start=0, end=0.6), Word(text="mundo", start=0.7, end=1.5)),
    ),))
    assert SubtitleTrack.model_validate_json(track.model_dump_json()) == track
    assert track.segments[0].words[1].start == 0.7
    with pytest.raises(ValidationError):
        track.segments[0].words[0].end = 10


@pytest.mark.parametrize("start,end", [(-1, 2), (1, 1), (2, 1), (float('nan'), 2), (0, float('inf')), (0, float('-inf'))])
def test_invalid_times(start, end):
    with pytest.raises(ValidationError):
        Word(text="fala", start=start, end=end)


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_text(text):
    with pytest.raises(ValidationError):
        Word(text=text, start=0, end=1)


def test_external_track_without_words_and_adjacent_segments():
    track = SubtitleTrack(segments=(Segment(text="A", start=0, end=1), Segment(text="B", start=1, end=2)))
    assert track.segments[0].words == ()
    assert SubtitleTrack().segments == ()


@pytest.mark.parametrize("intervals", [((0, 2), (1, 3)), ((2, 3), (0, 1))])
def test_unordered_or_overlapping_segments(intervals):
    with pytest.raises(ValidationError):
        SubtitleTrack(segments=tuple(Segment(text="x", start=a, end=b) for a, b in intervals))


@pytest.mark.parametrize("words", [
    [(0, 0.7), (0.5, 1)], [(0.5, 1), (0, 0.5)], [(0, 2.1)],
])
def test_invalid_word_order_or_containment(words):
    with pytest.raises(ValidationError):
        Segment(text="x", start=0, end=2, words=tuple(Word(text="x", start=a, end=b) for a, b in words))


def test_request_defaults_and_external_path_without_io(tmp_path):
    video = tmp_path / "vídeo inexistente.MP4"
    request = SubtitleRequest(video_file=video)
    assert request.transcription_mode == "whisper_only"
    assert request.custom_style.cpl == 40
    external = SubtitleRequest(video_file=video, transcription_mode="external", external_subtitle_file=tmp_path / "fala.srt")
    assert external.external_subtitle_file.suffix == ".srt"
    assert not video.exists()


@pytest.mark.parametrize("kwargs", [
    {"video_file": ""}, {"video_file": "file.avi"},
    {"transcription_mode": "unknown"}, {"style_preset": "unknown"},
    {"language": "pt-BR"}, {"transcription_mode": "external"},
    {"external_subtitle_file": "file.srt"},
    {"transcription_mode": "external", "external_subtitle_file": "file.exe"},
])
def test_invalid_request(kwargs):
    values = {"video_file": "video.mp4", **kwargs}
    with pytest.raises(ValidationError):
        SubtitleRequest(**values)


@pytest.mark.parametrize("kwargs", [
    {"active_color": "red"}, {"inactive_color": "#12345678"},
    {"font_size": 0}, {"font_size": True}, {"font_size": 201},
    {"alignment": 10}, {"margin_vertical": -1},
    {"inactive_opacity": float('nan')}, {"inactive_opacity": 2},
    {"cpl": 36}, {"cpl": 43}, {"font_name": "Arial,Injected"},
    {"font_name": "Arial\\tag"}, {"font_name": "  "}, {"unexpected": 1},
])
def test_invalid_styles(kwargs):
    with pytest.raises(ValidationError):
        CustomStyle(**kwargs)


def test_valid_style():
    style = CustomStyle(active_color="#00ffCC", inactive_color="#FFFFFF", font_name="Montserrat Black", font_size=72, alignment=5, inactive_opacity=0.8)
    assert style.font_size == 72


def test_job_public_serialization_and_utc():
    accepted = JobAccepted(created_at=datetime(2026, 10, 24, 12, tzinfo=timezone(timedelta(hours=-3))))
    assert accepted.created_at.hour == 15
    assert accepted.created_at.utcoffset() == timedelta(0)
    assert JobAccepted.model_validate_json(accepted.model_dump_json()) == accepted
    progress = JobProgress(job_id=accepted.job_id)
    assert len(progress.steps) == 5
    assert set(progress.steps.values()) == {"PENDING"}
    job = Job(job_id=accepted.job_id, progress=progress, output_path=Path("output/video.mp4"))
    public = JobAccepted(job_id=job.job_id, status=job.status, created_at=job.created_at)
    assert "output_path" not in public.model_dump_json()


@pytest.mark.parametrize("pct", [-1, 101, True, 1.5, float('inf')])
def test_invalid_job_progress(pct):
    with pytest.raises(ValidationError):
        JobProgress(job_id=uuid4(), progress_pct=pct)


def test_invalid_job_timestamp_and_mismatch():
    with pytest.raises(ValidationError):
        JobAccepted(created_at=datetime(2026, 10, 24))
    with pytest.raises(ValidationError):
        Job(progress=JobProgress(job_id=uuid4()))
    job_id = uuid4()
    with pytest.raises(ValidationError):
        Job(job_id=job_id, status=JobStatus.FAILED, progress=JobProgress(job_id=job_id))
