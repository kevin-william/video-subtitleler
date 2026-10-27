from types import SimpleNamespace as NS

import pytest

from video_subtitleler.services.transcriber import Transcriber, TranscriptionError


def test_windows_cuda_dll_directories(monkeypatch, tmp_path):
    import os
    from video_subtitleler.services import transcriber

    if os.name != "nt":
        pytest.skip("Registro de DLLs exclusivo do Windows")
    for package in ("cublas", "cudnn", "cuda_nvrtc"):
        (tmp_path / "nvidia" / package / "bin").mkdir(parents=True)
    monkeypatch.setattr(transcriber.sysconfig, "get_path", lambda _: str(tmp_path))
    opened = []
    monkeypatch.setattr(transcriber.os, "add_dll_directory", lambda path: opened.append(path) or path)
    monkeypatch.setenv("PATH", "original")
    transcriber._prepare_windows_cuda.cache_clear()
    try:
        handles = transcriber._prepare_windows_cuda()
        assert len(handles) == 3
        assert all(path in os.environ["PATH"].split(os.pathsep) for path in opened)
        assert os.environ["PATH"].endswith(os.pathsep + "original")
        assert transcriber._prepare_windows_cuda() is handles
        assert len(opened) == 3
    finally:
        transcriber._prepare_windows_cuda.cache_clear()


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


def test_whisper_sanitizes_zero_duration_and_unordered_words(settings, tmp_path):
    class Model:
        def transcribe(self, audio, **kwargs):
            return iter([
                NS(
                    text=" ainda em 2020",
                    start=34.0,
                    end=36.0,
                    words=[
                        NS(word=" ainda", start=34.22, end=34.42),
                        NS(word=" em", start=34.42, end=34.42),
                        NS(word=" 2020", start=34.42, end=35.06),
                    ],
                )
            ]), NS(language="pt")

    service = Transcriber(settings, lambda *a, **k: Model())
    track = service.transcribe(tmp_path / "a.wav")
    assert len(track.segments) == 1
    words = track.segments[0].words
    assert len(words) == 3
    assert words[0].text == "ainda"
    assert words[1].text == "em"
    assert words[1].start < words[1].end
    assert words[2].text == "2020"
    assert words[1].end <= words[2].start


@pytest.mark.integration_whisper
def test_real_whisper_local_voice(settings):
    import os
    from pathlib import Path
    voice, model = os.environ.get("SUBTITLE_TEST_VOICE"), os.environ.get("SUBTITLE_TEST_MODEL")
    if not voice or not model or not Path(voice).is_file() or not Path(model).is_dir():
        pytest.skip("Defina SUBTITLE_TEST_VOICE e SUBTITLE_TEST_MODEL com voz autorizada e pesos locais.")
    pytest.importorskip("faster_whisper")
    configured = settings.model_copy(update={
        "whisper_model": model,
        "whisper_device": os.environ.get("SUBTITLE_TEST_DEVICE", settings.whisper_device),
        "whisper_compute_type": os.environ.get("SUBTITLE_TEST_COMPUTE_TYPE", settings.whisper_compute_type),
    })
    track = Transcriber(configured).transcribe(Path(voice), "en")
    words = [word for segment in track.segments for word in segment.words]
    assert len(words) >= 5
    assert all(word.start < word.end for word in words)
