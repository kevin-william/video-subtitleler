import re

import pytest

from video_subtitleler.models.schema import CustomStyle
from video_subtitleler.models.subtitles import Segment, SubtitleTrack, Word
from video_subtitleler.services.ass_builder import ASSBuilder, ass_time, color
from video_subtitleler.services.external_subtitles import SubtitleError


def events(text):
    return [line for line in text.splitlines() if line.startswith("Dialogue:")]


def test_movie_headers_colors_and_times(track):
    text = ASSBuilder().build(track, "movie_series", width=640, height=360)
    assert "[V4+ Styles]" in text and "[Events]" in text
    assert "PlayResX: 640" in text
    assert ",0:00:00.10,0:00:01.60," in text
    assert color("#123456") == "&H00563412"
    assert ass_time(366101) == "1:01:01.01"


@pytest.mark.parametrize("text", ["palavra " * 50, "A" * 120, "áéí çã " * 50])
def test_movie_maximum_two_lines_and_cpl(text):
    track = SubtitleTrack(segments=(Segment(text=text, start=0, end=15),))
    result = events(ASSBuilder().build(track, "movie_series"))
    assert len(result) > 1
    for event in result:
        lines = event.split(",", 9)[9].split("\\N")
        assert len(lines) <= 2
        assert all(len(line) <= 40 for line in lines)


def test_unsafe_text_cannot_inject_ass():
    track = SubtitleTrack(segments=(Segment(text=r"{\pos(0,0)} hello\Nworld", start=0, end=1),))
    text = events(ASSBuilder().build(track, "movie_series"))[0].split(",", 9)[9]
    assert "{" not in text and "\\" not in text


def test_empty_or_short_interval():
    builder = ASSBuilder()
    with pytest.raises(SubtitleError):
        builder.build(SubtitleTrack(), "movie_series")
    with pytest.raises(SubtitleError):
        builder.build(SubtitleTrack(segments=(Segment(text="a", start=0, end=0.001),)), "movie_series")
