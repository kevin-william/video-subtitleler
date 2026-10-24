"""Operações de mídia executadas sem shell."""

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from video_subtitleler.config import Settings


class MediaError(RuntimeError):
    pass


def run_media(args: list[str], timeout: float, *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd)
    except FileNotFoundError as exc:
        raise MediaError("Executável de mídia não encontrado; configure FFmpeg/FFprobe.") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaError("Tempo limite de processamento de mídia excedido.") from exc
    except OSError as exc:
        raise MediaError("Não foi possível executar o processamento de mídia.") from exc
    if result.returncode:
        raise MediaError("FFmpeg/FFprobe recusou a mídia ou a configuração de processamento.")
    return result.stdout


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    width: int
    height: int
    has_audio: bool


class AudioService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def probe(self, video: Path) -> MediaInfo:
        video = Path(video)
        if video.suffix.lower() != ".mp4" or not video.is_file():
            raise MediaError("Informe um arquivo MP4 existente.")
        raw = run_media([self.settings.ffprobe_path, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video.resolve())], self.settings.media_timeout)
        try:
            data = json.loads(raw)
            stream = next(s for s in data["streams"] if s["codec_type"] == "video")
            duration = float(data["format"]["duration"])
            width, height = int(stream["width"]), int(stream["height"])
            rotation = float(stream.get("tags", {}).get("rotate", 0))
            for side in stream.get("side_data_list", []):
                if "rotation" in side:
                    rotation = float(side["rotation"])
            if not math.isfinite(rotation):
                raise ValueError("invalid rotation")
            if round(rotation) % 180 == 90:
                width, height = height, width
            if not math.isfinite(duration) or duration <= 0 or min(width, height) <= 0:
                raise ValueError("invalid metadata")
            if "mp4" not in data["format"].get("format_name", "").split(","):
                raise ValueError("not mp4 container")
            return MediaInfo(duration, width, height, any(s["codec_type"] == "audio" for s in data["streams"]))
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise MediaError("MP4 inválido ou sem vídeo/duração válida.") from exc

    def extract(self, video: Path, destination: Path) -> Path:
        if not self.probe(video).has_audio:
            raise MediaError("Vídeo sem faixa de áudio para transcrição.")
        destination = Path(destination)
        if destination.exists() or destination.resolve() == Path(video).resolve():
            raise MediaError("O destino de áudio já existe.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            run_media([self.settings.ffmpeg_path, "-nostdin", "-v", "error", "-n", "-i", str(Path(video).resolve()), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destination.resolve())], self.settings.media_timeout)
            if not destination.is_file() or destination.stat().st_size <= 44:
                raise MediaError("FFmpeg não produziu áudio válido.")
            return destination
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
