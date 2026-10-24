from types import SimpleNamespace as NS

import pytest

from video_subtitleler.services.transcriber import Transcriber, TranscriptionError


def test_whisper_parameters_and_lazy_loading(settings, tmp_path):
    calls = []
    class Model:
        def transcribe(self, audio, **kwargs):
            calls.append(kwargs)
            return iter([NS(text=" Olá", start=0.1, end=0.7, words=[NS(word=" Olá", start=0.1, end=0.7)])]), NS(language="pt")
    loaded = []
    def factory(*args, **kwargs):
        loaded.append((args, kwargs))
        return Model()
    service = Transcriber(settings, factory)
    assert not loaded
    track = service.transcribe(tmp_path / "a.wav")
    service.transcribe(tmp_path / "a.wav", "pt")
    assert len(loaded) == 1
    assert calls == [{"language": None, "word_timestamps": True}, {"language": "pt", "word_timestamps": True}]
    assert track.segments[0].words[0].start == 0.1


@pytest.mark.parametrize("failure", ["load", "iterator", "silence"])
def test_whisper_failures(settings, tmp_path, failure):
    def factory(*a, **k):
        if failure == "load":
            raise RuntimeError("load failed")
        def iterator():
            if failure == "iterator":
                raise RuntimeError("late failure")
            yield from []
        return NS(transcribe=lambda *a, **k: (iterator(), NS(language="pt")))
    with pytest.raises(TranscriptionError):
        Transcriber(settings, factory).transcribe(tmp_path / "a.wav")


@pytest.mark.integration_whisper
def test_real_whisper_local_voice(settings):
    import os
    from pathlib import Path
    voice, model = os.environ.get("SUBTITLE_TEST_VOICE"), os.environ.get("SUBTITLE_TEST_MODEL")
    if not voice or not model or not Path(voice).is_file() or not Path(model).is_dir():
        pytest.skip("Defina SUBTITLE_TEST_VOICE e SUBTITLE_TEST_MODEL com voz autorizada e pesos locais.")
    pytest.importorskip("faster_whisper")
    configured = settings.model_copy(update={"whisper_model": model})
    track = Transcriber(configured).transcribe(Path(voice), "en")
    words = [word for segment in track.segments for word in segment.words]
    assert len(words) >= 5
    assert all(word.start < word.end for word in words)
