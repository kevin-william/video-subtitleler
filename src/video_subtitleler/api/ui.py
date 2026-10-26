"""Página local e configuração pública mínima; não inicializa o pipeline."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from video_subtitleler.config import Settings

STATIC_DIR = Path(__file__).resolve().parent / "static"
router = APIRouter()


class UIConfig(BaseModel):
    max_upload_bytes: int = Field(gt=0)


@router.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/api/v1/ui-config", response_model=UIConfig)
def ui_config(request: Request):
    try:
        with request.app.state.pipeline_lock:
            if request.app.state.settings is None:
                request.app.state.settings = Settings()
            return UIConfig(max_upload_bytes=request.app.state.settings.max_upload_bytes)
    except (ValidationError, OSError):
        raise HTTPException(503, "Não foi possível carregar a configuração do serviço.") from None
