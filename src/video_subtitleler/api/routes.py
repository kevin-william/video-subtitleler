import json
import tempfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from video_subtitleler.models.schema import CustomStyle, JobAccepted, JobProgress, JobStatus, StylePreset, SubtitleRequest, TranscriptionMode
from video_subtitleler.services.audio import MediaError
from video_subtitleler.services.external_subtitles import SubtitleError
from video_subtitleler.services.pipeline import Pipeline
from video_subtitleler.storage.job_store import JobNotFound
from .dependencies import get_pipeline

router = APIRouter(prefix="/api/v1")
PipelineDependency = Annotated[Pipeline, Depends(get_pipeline)]


def execute_job(pipeline, request, job_id, temporary):
    try:
        pipeline.run(request, job_id)
    finally:
        temporary.cleanup()


async def save_upload(upload: UploadFile, path: Path, remaining: int) -> int:
    size = 0
    with path.open("xb") as file:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > remaining:
                raise HTTPException(413, "Limite de upload excedido.")
            file.write(chunk)
    if size == 0:
        raise HTTPException(422, "Arquivo vazio.")
    return size


@router.post("/subtitles/generate", status_code=202, response_model=JobAccepted)
async def generate(
    background_tasks: BackgroundTasks,
    pipeline: PipelineDependency,
    video_file: Annotated[UploadFile, File()],
    transcription_mode: Annotated[TranscriptionMode, Form()] = TranscriptionMode.WHISPER_ONLY,
    style_preset: Annotated[StylePreset, Form()] = StylePreset.MOVIE_SERIES,
    external_subtitle_file: Annotated[UploadFile | None, File()] = None,
    language: Annotated[str, Form()] = "auto",
    custom_style: Annotated[str, Form()] = "{}",
):
    temporary = None
    scheduled = False
    try:
        suffix = Path((video_file.filename or "").replace("\\", "/")).suffix.lower()
        ext = Path((external_subtitle_file.filename or "").replace("\\", "/")).suffix.lower() if external_subtitle_file else None
        if suffix != ".mp4" or (ext is not None and ext not in {".srt", ".vtt", ".json"}):
            raise HTTPException(422, "Extensão de arquivo inválida.")
        # Validate cheap fields before persisting any uploaded data.
        style = CustomStyle.model_validate(json.loads(custom_style))
        SubtitleRequest(video_file=Path("input.mp4"), transcription_mode=transcription_mode, style_preset=style_preset, external_subtitle_file=Path("external" + ext) if ext else None, language=language, custom_style=style)
        pipeline.settings.work_dir.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="upload-", dir=pipeline.settings.work_dir)
        folder = Path(temporary.name)
        video = folder / "input.mp4"
        consumed = await save_upload(video_file, video, pipeline.settings.max_upload_bytes)
        external = folder / ("external" + ext) if ext else None
        if external:
            await save_upload(external_subtitle_file, external, pipeline.settings.max_upload_bytes - consumed)
        await run_in_threadpool(pipeline.audio.probe, video)
        if external:
            track = await run_in_threadpool(pipeline.external_loader, external)
            if style_preset == StylePreset.INSTAGRAM_MUSIC and any(not s.words for s in track.segments):
                raise HTTPException(422, "Karaokê externo exige JSON com palavras alinhadas.")
        request = SubtitleRequest(video_file=video, transcription_mode=transcription_mode, style_preset=style_preset, external_subtitle_file=external, language=language, custom_style=style)
        job = pipeline.store.create()
        background_tasks.add_task(execute_job, pipeline, request, job.job_id, temporary)
        scheduled = True
        return JobAccepted(job_id=job.job_id, status=job.status, created_at=job.created_at)
    except (ValidationError, ValueError, MediaError, SubtitleError):
        raise HTTPException(422, "Parâmetros ou conteúdo dos arquivos inválidos.")
    finally:
        await video_file.close()
        if external_subtitle_file:
            await external_subtitle_file.close()
        if temporary and not scheduled:
            temporary.cleanup()


def find_job(pipeline, job_id):
    try:
        return pipeline.store.get(job_id)
    except JobNotFound:
        raise HTTPException(404, "Job não encontrado.")


@router.get("/jobs/{job_id}", response_model=JobProgress)
def status(job_id: UUID, pipeline: PipelineDependency):
    return find_job(pipeline, job_id).progress


@router.get("/jobs/{job_id}/download")
def download(job_id: UUID, pipeline: PipelineDependency):
    job = find_job(pipeline, job_id)
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(409, "Job ainda não possui saída concluída.")
    if job.output_path is None or not job.output_path.is_file():
        raise HTTPException(404, "Arquivo de saída não encontrado.")
    return FileResponse(job.output_path, media_type="video/mp4", filename=f"{job.job_id}.mp4")
