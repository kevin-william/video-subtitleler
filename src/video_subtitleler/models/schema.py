"""Contratos compartilhados pela biblioteca e futuras interfaces."""

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from .subtitles import Contract, Text


class TranscriptionMode(StrEnum):
    EXTERNAL = "external"
    WHISPER_ONLY = "whisper_only"
    LLM_HYBRID = "llm_hybrid"


class StylePreset(StrEnum):
    MOVIE_SERIES = "movie_series"
    INSTAGRAM_MUSIC = "instagram_music"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class JobStep(StrEnum):
    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIPTION = "transcription"
    LLM_ENHANCEMENT = "llm_enhancement"
    GENERATE_ASS = "generate_ass"
    BURNING_SUBTITLES = "burning_subtitles"


Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class CustomStyle(Contract):
    active_color: Color | None = None
    inactive_color: Color | None = None
    font_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    font_size: Annotated[int, Field(strict=True, ge=8, le=200)] | None = None
    alignment: Annotated[int, Field(strict=True, ge=1, le=9)] | None = None
    margin_vertical: Annotated[int, Field(strict=True, ge=0, le=4096)] | None = None
    inactive_opacity: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    cpl: Annotated[int, Field(strict=True, ge=37, le=42)] = 40

    @field_validator("font_name")
    @classmethod
    def safe_font(cls, value: str | None) -> str | None:
        if value and any(c in ",{}\\" or ord(c) < 32 for c in value):
            raise ValueError("nome de fonte contém caracteres de controle ASS")
        return value


class SubtitleRequest(Contract):
    video_file: Path
    transcription_mode: TranscriptionMode = TranscriptionMode.WHISPER_ONLY
    style_preset: StylePreset = StylePreset.MOVIE_SERIES
    external_subtitle_file: Path | None = None
    language: Annotated[str, Field(pattern=r"^(auto|[a-z]{2,3})$")] = "auto"
    custom_style: CustomStyle = Field(default_factory=CustomStyle)

    @field_validator("video_file", "external_subtitle_file", mode="before")
    @classmethod
    def nonempty_path(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("caminho vazio")
        return value

    @model_validator(mode="after")
    def check_files(self) -> Self:
        if self.video_file.suffix.lower() != ".mp4":
            raise ValueError("video_file deve ter extensão .mp4")
        if self.transcription_mode == TranscriptionMode.EXTERNAL:
            if self.external_subtitle_file is None:
                raise ValueError("modo external exige external_subtitle_file")
        elif self.external_subtitle_file is not None:
            raise ValueError("external_subtitle_file exige modo external")
        if self.external_subtitle_file and self.external_subtitle_file.suffix.lower() not in {".srt", ".vtt", ".json"}:
            raise ValueError("legenda deve ser .srt, .vtt ou .json")
        return self


class JobAccepted(Contract):
    job_id: UUID = Field(default_factory=uuid4)
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: Text = "Job aceito para processamento em background."

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at exige timezone")
        return value.astimezone(timezone.utc)


class JobProgress(Contract):
    job_id: UUID
    status: JobStatus = JobStatus.QUEUED
    progress_pct: Annotated[int, Field(strict=True, ge=0, le=100)] = 0
    current_step: JobStep | None = None
    steps: dict[JobStep, StepStatus] = Field(
        default_factory=lambda: {step: StepStatus.PENDING for step in JobStep}
    )
    error: str | None = None


class Job(JobAccepted):
    """Registro interno. Publicar apenas JobAccepted/JobProgress nas interfaces."""

    progress: JobProgress | None = None
    output_path: Path | None = None

    @model_validator(mode="after")
    def consistent_progress(self) -> Self:
        if self.progress and (self.progress.job_id != self.job_id or self.progress.status != self.status):
            raise ValueError("progresso e registro devem referir-se ao mesmo job/estado")
        return self
