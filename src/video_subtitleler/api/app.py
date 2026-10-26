import threading

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from video_subtitleler.config import Settings
from .routes import router
from .ui import STATIC_DIR, router as ui_router


def create_app(settings: Settings | None = None, pipeline=None) -> FastAPI:
    application = FastAPI(title="Video Subtitleler", version="0.1.0")
    application.state.settings = settings if settings is not None else getattr(pipeline, "settings", None)
    application.state.pipeline = pipeline
    application.state.pipeline_lock = threading.Lock()
    application.include_router(router)
    if not (STATIC_DIR / "index.html").is_file():
        raise RuntimeError("Interface web ausente. Reinstale o pacote com seus arquivos estáticos.")
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    application.include_router(ui_router)
    return application


app = create_app()
