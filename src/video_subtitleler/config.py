"""Configuração sem efeitos colaterais: instanciar Settings explicitamente."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUBTITLE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    work_dir: Path = Path("work")
    output_dir: Path = Path("output")
    database_path: Path = Path("work/jobs.sqlite3")
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    llm_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    llm_base_url: HttpUrl | None = None
    llm_model: str = "deepseek-chat"
    llm_timeout: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 30.0
    media_timeout: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 600.0
    max_upload_bytes: Annotated[int, Field(gt=0)] = 500_000_000

    @field_validator("ffmpeg_path", "ffprobe_path", "whisper_model", "whisper_device", "whisper_compute_type", "llm_model")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("valor não pode ser vazio")
        return value

    @field_validator("work_dir", "output_dir", "database_path", mode="before")
    @classmethod
    def nonempty_path(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("caminho não pode ser vazio")
        return value
