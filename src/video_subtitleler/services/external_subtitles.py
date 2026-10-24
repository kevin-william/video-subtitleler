"""Leitores estritos para o subconjunto textual de SRT e WebVTT."""

import html
import re
from pathlib import Path

from pydantic import ValidationError

from video_subtitleler.models.subtitles import Segment, SubtitleTrack


class SubtitleError(ValueError):
    pass


def timestamp(value: str, *, vtt: bool) -> float:
    pattern = r"(?:(\d{2,}):)?(\d{2}):(\d{2})\.(\d{3})" if vtt else r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})"
    match = re.fullmatch(pattern, value)
    if not match:
        raise SubtitleError("Timestamp de legenda inválido.")
    h, m, s, ms = match.groups()
    if int(m) > 59 or int(s) > 59:
        raise SubtitleError("Timestamp de legenda fora da faixa.")
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def load_external(path: Path) -> SubtitleTrack:
    try:
        path = Path(path)
        if path.suffix.lower() not in {".json", ".srt", ".vtt"}:
            raise SubtitleError("Formato externo deve ser SRT, VTT ou JSON.")
        content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
        if not content:
            raise SubtitleError("Legenda externa vazia.")
        if path.suffix.lower() == ".json":
            track = SubtitleTrack.model_validate_json(content)
        else:
            vtt = path.suffix.lower() == ".vtt"
            if vtt:
                lines = content.splitlines()
                if not re.fullmatch(r"WEBVTT(?:[ \t].*)?", lines[0]):
                    raise SubtitleError("Cabeçalho WEBVTT ausente.")
                content = "\n".join(lines[1:]).strip()
            segments = []
            for block in re.split(r"\n[ \t]*\n", content):
                lines = block.splitlines()
                if vtt and lines and (lines[0].startswith("NOTE") or lines[0] in {"STYLE", "REGION"}):
                    continue
                if lines and "-->" not in lines[0]:
                    identifier = lines.pop(0)
                    if not vtt and not identifier.isdigit():
                        raise SubtitleError("Índice SRT inválido.")
                if len(lines) < 2 or " --> " not in lines[0]:
                    raise SubtitleError("Bloco de legenda inválido.")
                start, end = lines.pop(0).split(" --> ", 1)
                end = end.split()[0]  # WebVTT cue settings are deliberately ignored.
                text = html.unescape(re.sub(r"<[^>]*>", "", "\n".join(lines)))
                segments.append(Segment(text=text, start=timestamp(start, vtt=vtt), end=timestamp(end, vtt=vtt)))
            track = SubtitleTrack(segments=tuple(segments))
        if not track.segments:
            raise SubtitleError("Legenda externa sem segmentos.")
        return track
    except (OSError, UnicodeError, ValidationError) as exc:
        raise SubtitleError("Não foi possível ler a legenda externa; confira o formato e os tempos.") from exc
