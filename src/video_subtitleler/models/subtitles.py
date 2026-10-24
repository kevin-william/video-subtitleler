"""Tempos em segundos; intervalos ordenados e sem sobreposição."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Seconds = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class Word(Contract):
    text: Text
    start: Seconds
    end: Seconds

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end deve ser maior que start")
        return self


def check_order(items: tuple) -> None:
    for previous, current in zip(items, items[1:]):
        if current.start < previous.end:
            raise ValueError("intervalos devem estar ordenados e sem sobreposição")


class Segment(Word):
    words: tuple[Word, ...] = ()

    @model_validator(mode="after")
    def check_words(self) -> Self:
        check_order(self.words)
        if any(w.start < self.start or w.end > self.end for w in self.words):
            raise ValueError("palavras devem estar dentro do segmento")
        return self


class SubtitleTrack(Contract):
    language: Text = "auto"
    segments: tuple[Segment, ...] = ()

    @model_validator(mode="after")
    def check_segments(self) -> Self:
        check_order(self.segments)
        return self
