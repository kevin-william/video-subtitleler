"""ASS determinístico; karaokê destaca exclusivamente a palavra do intervalo."""

import textwrap
from pathlib import Path

from video_subtitleler.models.schema import CustomStyle, StylePreset
from video_subtitleler.models.subtitles import SubtitleTrack
from .external_subtitles import SubtitleError


def ass_time(centiseconds: int) -> str:
    h, rem = divmod(centiseconds, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def color(value: str) -> str:
    return "&H00" + value[5:7] + value[3:5] + value[1:3]


def literal(text: str) -> str:
    # Fullwidth glyphs prevent untrusted ASS overrides and backslash escapes.
    return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\r", " ").replace("\n", " ")


def lines(text: str, cpl: int) -> list[str]:
    return textwrap.wrap(" ".join(text.split()), width=cpl, break_long_words=True, break_on_hyphens=False) or [""]


class ASSBuilder:
    def build(self, track: SubtitleTrack, preset: StylePreset, style: CustomStyle | None = None, *, width: int = 1920, height: int = 1080) -> str:
        if width <= 0 or height <= 0:
            raise SubtitleError("Resolução de vídeo inválida.")
        if not track.segments:
            raise SubtitleError("Não há legendas para gerar ASS.")
        style = style or CustomStyle()
        karaoke = preset == StylePreset.INSTAGRAM_MUSIC
        font = style.font_name or ("Impact" if karaoke else "Arial")
        size = style.font_size or (max(24, round(height * 0.07)) if karaoke else max(18, round(height * 0.045)))
        alignment = style.alignment or (5 if karaoke else 2)
        margin = style.margin_vertical if style.margin_vertical is not None else round(height * 0.06)
        active = color(style.active_color or ("#00FFCC" if karaoke else "#FFFFFF"))
        inactive = color(style.inactive_color or "#FFFFFF")
        opacity = style.inactive_opacity if style.inactive_opacity is not None else 0.85
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{active},{inactive},&H00000000,&H80000000,{-1 if karaoke else 0},0,0,0,100,100,0,0,1,2,1,{alignment},20,20,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []

        def emit(start, end, text):
            a, b = round(start * 100), round(end * 100)
            if b <= a:
                raise SubtitleError("Intervalo curto demais para a precisão de centésimos do ASS.")
            events.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{text}")

        for segment in track.segments:
            if karaoke:
                if not segment.words:
                    raise SubtitleError("Karaokê exige timestamps reais por palavra; use JSON alinhado ou Whisper.")
                for offset in range(0, len(segment.words), 5):
                    group = segment.words[offset:offset + 5]
                    boundaries = sorted({w.start for w in group} | {w.end for w in group})
                    for start, end in zip(boundaries, boundaries[1:]):
                        if round(end * 100) <= round(start * 100):
                            raise SubtitleError("Palavra ou pausa curta demais para ASS.")
                        pieces = []
                        line_length = 0
                        line_limit = max(8, int((width - 40) / (size * 0.65)))
                        for word in group:
                            on = word.start <= start < word.end
                            rgb = (active if on else inactive)[4:]
                            alpha = 0 if on else round((1 - opacity) * 255)
                            separator = "" if not pieces else "\\h"
                            if pieces and line_length + 1 + len(word.text) > line_limit:
                                separator = "\\N"
                                line_length = 0
                            pieces.append(separator + f"{{\\1c&H{rgb}&\\1a&H{alpha:02X}&}}{literal(word.text)}")
                            line_length += len(word.text) + 1
                        emit(start, end, "".join(pieces))
            else:
                # With words, split on word boundaries and retain real timestamps.
                if segment.words and all(len(w.text) <= style.cpl for w in segment.words):
                    groups, current = [], []
                    for word in segment.words:
                        candidate = " ".join(w.text for w in [*current, word])
                        if current and len(lines(candidate, style.cpl)) > 2:
                            groups.append(current)
                            current = []
                        current.append(word)
                    if current:
                        groups.append(current)
                    for group in groups:
                        emit(group[0].start, group[-1].end, "\\N".join(literal(line) for line in lines(" ".join(w.text for w in group), style.cpl)))
                else:
                    wrapped = lines(segment.text, style.cpl)
                    blocks = [wrapped[i:i + 2] for i in range(0, len(wrapped), 2)]
                    total = sum(sum(len(line) for line in block) for block in blocks)
                    cursor = segment.start
                    for index, block in enumerate(blocks):
                        end = segment.end if index == len(blocks) - 1 else cursor + (segment.end - segment.start) * sum(map(len, block)) / total
                        emit(cursor, end, "\\N".join(literal(line) for line in block))
                        cursor = end
        return header + "\n".join(events) + "\n"

    def write(self, destination: Path, *args, **kwargs) -> Path:
        content = self.build(*args, **kwargs)
        Path(destination).write_text(content, encoding="utf-8-sig")
        return Path(destination)
