import threading

from fastapi import FastAPI

from video_subtitleler.config import Settings
from .routes import router


def create_app(settings: Settings | None = None, pipeline=None) -> FastAPI:
    application = FastAPI(title="Video Subtitleler", version="0.1.0")
    application.state.settings = settings
    application.state.pipeline = pipeline
    application.state.pipeline_lock = threading.Lock()
    application.include_router(router)
    return application


app = create_app()
