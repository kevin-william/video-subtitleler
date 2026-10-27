import threading
import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from video_subtitleler.config import Settings
from video_subtitleler.observability import check_health, metrics
from .routes import router
from .ui import STATIC_DIR, router as ui_router


def create_app(settings: Settings | None = None, pipeline=None) -> FastAPI:
    application = FastAPI(title="Video Subtitleler", version="0.1.0")
    application.state.settings = settings if settings is not None else getattr(pipeline, "settings", None)
    application.state.pipeline = pipeline
    application.state.pipeline_lock = threading.Lock()

    @application.middleware("http")
    async def observability_middleware(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - t0

        path = request.url.path
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[:3] == ["api", "v1", "jobs"]:
            if len(parts) == 4 and parts[3] == "download":
                metric_path = "/api/v1/jobs/{job_id}/download"
            elif len(parts) == 3:
                metric_path = "/api/v1/jobs/{job_id}"
            else:
                metric_path = path
        else:
            metric_path = path

        metrics.record_http_request(
            method=request.method,
            path=metric_path,
            status=response.status_code,
            duration=duration,
        )
        return response

    @application.get("/healthz", include_in_schema=False)
    def healthz():
        return {"status": "ok"}

    @application.get("/health", include_in_schema=False)
    def health():
        st = application.state.settings or getattr(application.state.pipeline, "settings", None)
        if st is None:
            st = Settings(_env_file=None)
        store = getattr(application.state.pipeline, "store", None)
        result = check_health(st, store)
        return JSONResponse(content=result, status_code=result["http_code"])

    @application.get("/metrics", include_in_schema=False)
    def prometheus_metrics():
        return Response(
            content=metrics.to_prometheus_text(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    application.include_router(router)
    if not (STATIC_DIR / "index.html").is_file():
        raise RuntimeError("Interface web ausente. Reinstale o pacote com seus arquivos estáticos.")
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    application.include_router(ui_router)
    return application


app = create_app()
