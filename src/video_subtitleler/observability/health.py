"""Verificações de integridade e diagnósticos de saúde da aplicação."""

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Any

from video_subtitleler.config import Settings


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


def check_health(settings: Settings, store: Any = None) -> dict[str, Any]:
    """Executa verificações de saúde nos componentes e dependências do serviço."""
    checks: dict[str, Any] = {}
    is_healthy = True
    is_degraded = False

    # 1. Verificação do Banco de Dados / Job Store
    t0 = time.perf_counter()
    try:
        if store is not None and hasattr(store, "_connect"):
            with store._connect() as conn:
                conn.execute("SELECT 1").fetchone()
        elif store is not None and hasattr(store, "_jobs"):
            # MemoryJobStore
            pass
        else:
            db_path = Path(settings.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db_path, timeout=5) as conn:
                conn.execute("SELECT 1").fetchone()
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        checks["database"] = {"status": "ok", "latency_ms": db_latency_ms}
    except Exception as exc:
        is_healthy = False
        checks["database"] = {"status": "error", "error": str(exc)}

    # 2. Verificação de Espaço em Disco
    try:
        work_dir = Path(settings.work_dir)
        check_path = work_dir if work_dir.exists() else work_dir.parent
        usage = shutil.disk_usage(check_path)
        free_gb = usage.free / (1024**3)
        disk_status = "ok"
        if free_gb < 0.5:
            disk_status = "warning"
            is_degraded = True
        checks["disk"] = {
            "status": disk_status,
            "free_gb": round(free_gb, 2),
            "work_dir": str(settings.work_dir),
            "output_dir": str(settings.output_dir),
        }
    except Exception as exc:
        is_degraded = True
        checks["disk"] = {"status": "warning", "error": str(exc)}

    # 3. Ferramentas de Mídia (FFmpeg e FFprobe)
    ffmpeg_ok = bool(shutil.which(settings.ffmpeg_path) or Path(settings.ffmpeg_path).is_file())
    ffprobe_ok = bool(shutil.which(settings.ffprobe_path) or Path(settings.ffprobe_path).is_file())
    if ffmpeg_ok and ffprobe_ok:
        checks["media_tools"] = {"status": "ok", "ffmpeg": "available", "ffprobe": "available"}
    else:
        # Se os binários não forem encontrados no PATH, marcar como warning ou error
        # Se rodando em ambiente sem FFmpeg instalado, sinalizar
        status = "error" if not (ffmpeg_ok or ffprobe_ok) else "warning"
        if status == "error":
            is_healthy = False
        else:
            is_degraded = True
        checks["media_tools"] = {
            "status": status,
            "ffmpeg": "available" if ffmpeg_ok else "not_found",
            "ffprobe": "available" if ffprobe_ok else "not_found",
        }

    # 4. Configuração do Whisper
    checks["whisper"] = {
        "status": "ok",
        "device": settings.whisper_device,
        "model": settings.whisper_model,
        "compute_type": settings.whisper_compute_type,
    }

    # 5. Configuração da LLM
    checks["llm"] = {
        "status": "ok",
        "configured": bool(settings.llm_api_key and settings.llm_base_url),
        "model": settings.llm_model,
        "provider": settings.llm_base_url.host if settings.llm_base_url else None,
    }

    if not is_healthy:
        overall_status = HealthStatus.UNHEALTHY
        http_code = 503
    elif is_degraded:
        overall_status = HealthStatus.DEGRADED
        http_code = 200
    else:
        overall_status = HealthStatus.HEALTHY
        http_code = 200

    return {
        "status": overall_status.value,
        "http_code": http_code,
        "checks": checks,
    }
