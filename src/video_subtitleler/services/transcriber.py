"""Adaptador lazy: importar este módulo não carrega pesos."""

import threading
from pathlib import Path

from video_subtitleler.config import Settings
from video_subtitleler.models.subtitles import Segment, SubtitleTrack, Word


class TranscriptionError(RuntimeError):
    pass


class Transcriber:
    def __init__(self, settings: Settings, model_factory=None):
        self.settings = settings
        self.model_factory = model_factory
        self._model = None
        self._lock = threading.Lock()

    def transcribe(self, audio: Path, language: str = "auto") -> SubtitleTrack:
        try:
            with self._lock:
                if self._model is None:
                    factory = self.model_factory
                    if factory is None:
                        from faster_whisper import WhisperModel
                        factory = WhisperModel
                    self._model = factory(self.settings.whisper_model, device=self.settings.whisper_device, compute_type=self.settings.whisper_compute_type)
                segments, info = self._model.transcribe(str(audio), language=None if language == "auto" else language, word_timestamps=True)
                result = []
                for segment in segments:
                    if not segment.text.strip():
                        continue
                    words = tuple(Word(text=w.word, start=w.start, end=w.end) for w in (segment.words or []) if w.word.strip())
                    result.append(Segment(text=segment.text, start=segment.start, end=segment.end, words=words))
                if not result:
                    raise TranscriptionError("Nenhuma fala reconhecida no áudio.")
                return SubtitleTrack(language=info.language, segments=tuple(result))
        except ImportError as exc:
            raise TranscriptionError('Instale o extra "whisper" para transcrever áudio.') from exc
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError("Falha na transcrição; confira o modelo e o alinhamento de palavras.") from exc
