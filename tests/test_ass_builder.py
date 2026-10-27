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


def test_karaoke_active_only_and_pause(track):
    text = ASSBuilder().build(track, "instagram_music")
    rows = events(text)
    assert len(rows) == 3  # first word, silence, second word
    assert all("Olá" in row and "mundo" in row for row in rows)
    active = r"\1c&HCCFF00&\1a&H00&"
    assert rows[0].count(active) == 1
    assert active not in rows[1]
    assert rows[2].count(active) == 1
    assert rows[0].index(active) < rows[0].index("Olá")
    assert rows[2].index(active) > rows[2].index("Olá")


def test_karaoke_groups_and_style():
    words = tuple(Word(text=f"w{i}", start=i, end=i + 0.5) for i in range(6))
    track = SubtitleTrack(segments=(Segment(text="words", start=0, end=5.5, words=words),))
    text = ASSBuilder().build(track, "instagram_music", CustomStyle(active_color="#FFD700", inactive_color="#112233", font_size=60, alignment=2, margin_vertical=200))
    assert ",60,&H0000D7FF,&H00332211," in text
    assert all(not ("w0" in row and "w5" in row) for row in events(text))


def test_missing_words_empty_or_subcentisecond():
    builder = ASSBuilder()
    with pytest.raises(SubtitleError):
        builder.build(SubtitleTrack(), "movie_series")
    with pytest.raises(SubtitleError):
        builder.build(SubtitleTrack(segments=(Segment(text="a", start=0, end=1),)), "instagram_music")
    with pytest.raises(SubtitleError):
        builder.build(SubtitleTrack(segments=(Segment(text="a", start=0, end=0.001),)), "movie_series")


def test_wrap_style_is_zero():
    track = SubtitleTrack(segments=(Segment(text="teste", start=0, end=1),))
    text = ASSBuilder().build(track, "movie_series")
    assert "WrapStyle: 0" in text


def test_large_font_adaptive_cpl_and_up_to_three_lines():
    # In vertical video 1080x1920 with large font 80, effective CPL will be ~23
    track = SubtitleTrack(segments=(Segment(text="Esta frase possui um texto longo o suficiente para precisar quebrar em várias linhas", start=0, end=10),))
    text = ASSBuilder().build(track, "movie_series", CustomStyle(font_size=80), width=1080, height=1920)
    rows = events(text)
    assert len(rows) >= 1
    for event in rows:
        event_lines = event.split(",", 9)[9].split("\\N")
        assert len(event_lines) <= 3
        # Each line should be within the adaptive CPL (usable_width=1040, 1040 / (80 * 0.55) = 23)
        assert all(len(line) <= 24 for line in event_lines)


def test_font_size_safe_ceiling_clamping():
    # If font size 200 is set on a 640x360 video, it must be clamped to safe ceiling
    track = SubtitleTrack(segments=(Segment(text="teste seguro", start=0, end=1),))
    text = ASSBuilder().build(track, "movie_series", CustomStyle(font_size=200), width=640, height=360)
    # Check that style doesn't use 200, but clamped safe size (<= 136)
    match = re.search(r"Style:\s*Default,[^,]+,(\d+),", text)
    assert match is not None
    used_size = int(match.group(1))
    assert used_size < 200
    assert used_size <= 136


def test_karaoke_large_font_adapts_group_size():
    words = tuple(Word(text=f"palavra{i}", start=i, end=i + 0.5) for i in range(10))
    track = SubtitleTrack(segments=(Segment(text="frase", start=0, end=10, words=words),))
    # In 1080x1920 with font_size=80, line_limit <= 27, group_size <= 4
    text = ASSBuilder().build(track, "instagram_music", CustomStyle(font_size=80), width=1080, height=1920)
    rows = events(text)
    # Ensure words are grouped into smaller chunks (not 5 words together)
    assert all(not ("palavra0" in r and "palavra4" in r) for r in rows)
