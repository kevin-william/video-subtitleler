"""Logging estruturado e contextual com job_id para o video-subtitleler."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

_job_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)


class JobContextFilter(logging.Filter):
    """Filtro de logging que injeta o job_id corrente em cada LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        job_id = _job_id_ctx.get()
        record.job_id = str(job_id) if job_id else "-"
        return True


@contextmanager
def job_context(job_id: UUID | str | None):
    """Context manager para associar o job_id atual aos logs e métricas."""
    token = _job_id_ctx.set(str(job_id) if job_id is not None else None)
    try:
        yield
    finally:
        _job_id_ctx.reset(token)


def get_current_job_id() -> str | None:
    """Retorna o job_id corrente no contexto, se houver."""
    return _job_id_ctx.get()


def get_logger(name: str) -> logging.Logger:
    """Obtém um logger com o filtro de contexto de job já configurado."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, JobContextFilter) for f in logger.filters):
        logger.addFilter(JobContextFilter())
    return logger


class JsonFormatter(logging.Formatter):
    """Formatador de log estruturado em JSON para ingestão por observabilidade."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "job_id": getattr(record, "job_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    level: int | str = logging.INFO,
    stream: Any = None,
    json_format: bool = False,
) -> None:
    """Configura o logger raiz do pacote com filtro de job_id e formato padronizado."""
    pkg_logger = logging.getLogger("video_subtitleler")
    pkg_logger.setLevel(level)

    # Remover handlers anteriores para evitar duplicações
    for handler in list(pkg_logger.handlers):
        pkg_logger.removeHandler(handler)

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)
    handler.addFilter(JobContextFilter())

    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] [job_id=%(job_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    pkg_logger.addHandler(handler)
