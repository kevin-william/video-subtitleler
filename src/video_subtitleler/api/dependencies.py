from fastapi import Request

from video_subtitleler.config import Settings
from video_subtitleler.services.pipeline import Pipeline


def get_pipeline(request: Request) -> Pipeline:
    with request.app.state.pipeline_lock:
        if request.app.state.pipeline is None:
            request.app.state.pipeline = Pipeline(request.app.state.settings or Settings())
        return request.app.state.pipeline
