"""Render por libass com arquivos temporários de nomes controlados."""

import os
import shutil
import tempfile
from pathlib import Path

from video_subtitleler.config import Settings
from .audio import AudioService, MediaError, run_media


class Renderer:
    def __init__(self, settings: Settings, audio: AudioService | None = None):
        self.settings = settings
        self.audio = audio or AudioService(settings)

    def render(self, video: Path, ass: Path, destination: Path) -> Path:
        video, ass, destination = Path(video).resolve(), Path(ass).resolve(), Path(destination).resolve()
        if destination.suffix.lower() != ".mp4" or destination.exists() or destination == video:
            raise MediaError("Destino MP4 deve ser novo e diferente da entrada.")
        original = self.audio.probe(video)
        if not ass.is_file():
            raise MediaError("Arquivo ASS não encontrado.")
        filters = run_media([self.settings.ffmpeg_path, "-hide_banner", "-filters"], self.settings.media_timeout)
        if not any(" ass " in line for line in filters.splitlines()):
            raise MediaError("FFmpeg sem filtro ass/libass.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="render-", dir=destination.parent) as temp:
            work = Path(temp)
            shutil.copyfile(ass, work / "subtitles.ass")
            result = work / "rendered.mp4"
            encoder = self.settings.render_encoder
            if encoder != "libx264":
                encoders = run_media([self.settings.ffmpeg_path, "-hide_banner", "-encoders"], self.settings.media_timeout)
                if encoder not in encoders:
                    raise MediaError("Encoder solicitado não está disponível.")
            args = [self.settings.ffmpeg_path, "-nostdin", "-v", "error", "-n", "-i", str(video), "-map", "0:v:0", "-map", "0:a:0?", "-vf", "ass=subtitles.ass", "-c:v", encoder]
            if encoder == "libx264":
                args += ["-preset", "fast", "-crf", "20"]
            args += ["-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(result)]
            run_media(args, self.settings.media_timeout, cwd=work)
            rendered = self.audio.probe(result)
            if (rendered.width, rendered.height) != (original.width, original.height) or abs(rendered.duration - original.duration) > 0.25 or rendered.has_audio != original.has_audio:
                raise MediaError("Saída renderizada não preservou as propriedades de mídia.")
            # A unique destination per job is required by the caller.
            if destination.exists():
                raise MediaError("Destino já existe.")
            os.replace(result, destination)
        return destination
