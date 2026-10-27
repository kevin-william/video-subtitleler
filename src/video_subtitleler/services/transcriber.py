"""Adaptador lazy: importar este módulo não carrega pesos."""

import os
import sysconfig
import threading
from functools import cache
from pathlib import Path

from video_subtitleler.config import Settings
from video_subtitleler.models.subtitles import Segment, SubtitleTrack, Word


class TranscriptionError(RuntimeError):
    pass


@cache
def _prepare_windows_cuda():
    """Expose NVIDIA pip DLLs only when GPU transcription is requested.

    Keep directory handles alive for the process; CTranslate2 also loads DLLs
    through LoadLibrary, which needs PATH in addition to add_dll_directory.
    """
    if os.name != "nt":
        return ()
    root = Path(sysconfig.get_path("purelib")) / "nvidia"
    directories = [root / package / "bin" for package in ("cublas", "cudnn", "cuda_nvrtc")]
    directories = [str(path) for path in directories if path.is_dir()]
    handles = tuple(os.add_dll_directory(path) for path in directories)
    if directories:
        os.environ["PATH"] = os.pathsep.join([*directories, os.environ.get("PATH", "")])
    return handles


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
                        if self.settings.whisper_device in {"cuda", "auto"}:
                            _prepare_windows_cuda()
                        from faster_whisper import WhisperModel
                        factory = WhisperModel
                    self._model = factory(self.settings.whisper_model, device=self.settings.whisper_device, compute_type=self.settings.whisper_compute_type)
                segments, info = self._model.transcribe(str(audio), language=None if language == "auto" else language, word_timestamps=True)
                result = []
                prev_seg_end = 0.0
                for segment in segments:
                    if not segment.text.strip():
                        continue
                    seg_start = max(float(segment.start), float(prev_seg_end))
                    seg_end = max(float(segment.end), seg_start + 0.02)
                    raw_words = [w for w in (segment.words or []) if getattr(w, "word", "").strip()]
                    words = ()
                    if raw_words:
                        words_list = []
                        prev_word_end = seg_start
                        for item in raw_words:
                            w_text = item.word.strip()
                            w_start = max(float(item.start), prev_word_end, seg_start)
                            w_end = max(float(item.end), w_start + 0.02)
                            if w_end > seg_end:
                                if seg_end > w_start + 0.01:
                                    w_end = seg_end
                                else:
                                    seg_end = w_end
                            if w_end > w_start:
                                try:
                                    w_obj = Word(text=w_text, start=w_start, end=w_end)
                                    words_list.append(w_obj)
                                    prev_word_end = w_obj.end
                                except Exception:
                                    pass
                        if words_list:
                            seg_start = min(seg_start, words_list[0].start)
                            seg_end = max(seg_end, words_list[-1].end)
                            try:
                                seg_candidate = Segment(text=segment.text, start=seg_start, end=seg_end, words=tuple(words_list))
                                words = seg_candidate.words
                            except Exception:
                                words = ()
                    result.append(Segment(text=segment.text, start=seg_start, end=seg_end, words=words))
                    prev_seg_end = seg_end
                if not result:
                    raise TranscriptionError("Nenhuma fala reconhecida no áudio.")
                return SubtitleTrack(language=info.language, segments=tuple(result))
        except ImportError as exc:
            raise TranscriptionError('Instale o extra "whisper" para transcrever áudio.') from exc
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError("Falha na transcrição; confira o modelo e o alinhamento de palavras.") from exc
