import pytest

from video_subtitleler.services.external_subtitles import SubtitleError, load_external


@pytest.mark.parametrize("suffix,content", [
    (".srt", "\ufeff1\n00:00:00,125 --> 00:00:01,500\nOlá\nmundo\n"),
    (".vtt", "WEBVTT\n\nNOTE comentário\nignorado\n\ncue1\n00:00.125 --> 00:01.500 align:center\nOlá\nmundo\n"),
])
def test_text_formats_preserve_times_without_inventing_words(tmp_path, suffix, content):
    path = tmp_path / ("sub" + suffix)
    path.write_text(content, encoding="utf-8")
    track = load_external(path)
    assert track.segments[0].start == 0.125
    assert track.segments[0].end == 1.5
    assert track.segments[0].text == "Olá\nmundo"
    assert track.segments[0].words == ()


def test_json_words_roundtrip(tmp_path, track):
    path = tmp_path / "sub.json"
    path.write_text(track.model_dump_json(), encoding="utf-8")
    assert load_external(path) == track


@pytest.mark.parametrize("suffix,content", [
    (".srt", ""), (".vtt", "1\n00:00:01,000 --> 00:00:02,000\ntexto"),
    (".json", '{"segments":[]}'), (".json", '{}invalid'),
    (".srt", "1\n00:61:00,000 --> 00:62:00,000\ntexto"),
    (".srt", "1\n00:00:02,000 --> 00:00:01,000\ntexto"),
    (".vtt", "WEBVTT\n\ninvalid"), (".exe", "texto"),
])
def test_invalid_external(tmp_path, suffix, content):
    path = tmp_path / ("sub" + suffix)
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SubtitleError):
        load_external(path)
