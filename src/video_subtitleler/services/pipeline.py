"""Orquestração síncrona compartilhada pela CLI e worker HTTP."""

import tempfile
import time
from pathlib import Path
from uuid import UUID

from video_subtitleler.config import Settings
from video_subtitleler.models.schema import JobProgress, JobStatus, JobStep, StepStatus, SubtitleRequest, TranscriptionMode
from video_subtitleler.observability import get_logger, job_context, metrics
from video_subtitleler.storage.job_store import SQLiteJobStore
from .ass_builder import ASSBuilder
from .audio import AudioService, MediaError
from .external_subtitles import SubtitleError, load_external
from .llm_enhancer import LLMEnhancer
from .renderer import Renderer
from .transcriber import Transcriber, TranscriptionError

logger = get_logger(__name__)


class Pipeline:
    def __init__(self, settings: Settings, store=None, *, audio=None, transcriber=None, enhancer=None, builder=None, renderer=None, external_loader=load_external):
        self.settings = settings
        self.store = store if store is not None else SQLiteJobStore(settings.database_path)
        self.audio = audio or AudioService(settings)
        self.transcriber = transcriber or Transcriber(settings)
        self.enhancer = enhancer or LLMEnhancer(settings)
        self.builder = builder or ASSBuilder()
        self.renderer = renderer or Renderer(settings, self.audio)
        self.external_loader = external_loader

    def run(self, request: SubtitleRequest, job_id: UUID | None = None, *, destination: Path | None = None, on_progress=None):
        job = self.store.create() if job_id is None else self.store.get(job_id)
        steps = {step: StepStatus.PENDING for step in JobStep}
        pct, current = 0, None
        t_job_start = time.perf_counter()
        t_step_start = t_job_start

        def update(status=JobStatus.PROCESSING, *, error=None, output=None):
            progress = JobProgress(job_id=job.job_id, status=status, progress_pct=pct, current_step=current, steps=dict(steps), error=error)
            result = self.store.update(progress, output)
            if on_progress:
                on_progress(progress)
            return result

        with job_context(job.job_id):
            logger.info("Iniciando job %s (modo: %s, preset: %s)", job.job_id, request.transcription_mode.value, request.style_preset.value)
            metrics.job_started()
            update()
            try:
                info = self.audio.probe(request.video_file)
                self.settings.work_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix=f"job-{job.job_id}-", dir=self.settings.work_dir) as folder:
                    work = Path(folder)
                    if request.transcription_mode == TranscriptionMode.EXTERNAL:
                        for step in (JobStep.EXTRACT_AUDIO, JobStep.TRANSCRIPTION, JobStep.LLM_ENHANCEMENT):
                            steps[step] = StepStatus.SKIPPED
                            metrics.record_step(step=step.value, status="SKIPPED")
                        track = self.external_loader(request.external_subtitle_file)
                    else:
                        current = JobStep.EXTRACT_AUDIO
                        steps[current] = StepStatus.RUNNING
                        t_step_start = time.perf_counter()
                        update()
                        wav = self.audio.extract(request.video_file, work / "audio.wav")
                        duration = time.perf_counter() - t_step_start
                        steps[current] = StepStatus.COMPLETED
                        metrics.record_step(step=current.value, status="COMPLETED", duration=duration)
                        logger.info("Etapa %s concluída em %.2fs", current.value, duration)

                        pct, current = 20, JobStep.TRANSCRIPTION
                        steps[current] = StepStatus.RUNNING
                        t_step_start = time.perf_counter()
                        update()
                        track = self.transcriber.transcribe(wav, request.language)
                        duration = time.perf_counter() - t_step_start
                        steps[current] = StepStatus.COMPLETED
                        metrics.record_step(step=current.value, status="COMPLETED", duration=duration)
                        logger.info("Etapa %s concluída em %.2fs", current.value, duration)

                        pct = 50
                        if request.transcription_mode == TranscriptionMode.LLM_HYBRID:
                            current = JobStep.LLM_ENHANCEMENT
                            steps[current] = StepStatus.RUNNING
                            t_step_start = time.perf_counter()
                            update()
                            original = track
                            track = self.enhancer.enhance_with_fallback(track, request.style_preset)
                            duration = time.perf_counter() - t_step_start
                            step_status = StepStatus.SKIPPED if track is original else StepStatus.COMPLETED
                            steps[current] = step_status
                            metrics.record_step(step=current.value, status=step_status.value, duration=duration)
                            logger.info("Etapa %s concluída (%s) em %.2fs", current.value, step_status.value, duration)
                        else:
                            steps[JobStep.LLM_ENHANCEMENT] = StepStatus.SKIPPED
                            metrics.record_step(step=JobStep.LLM_ENHANCEMENT.value, status="SKIPPED")

                    pct, current = 60, JobStep.GENERATE_ASS
                    steps[current] = StepStatus.RUNNING
                    t_step_start = time.perf_counter()
                    update()
                    ass = self.builder.write(work / "subtitles.ass", track, request.style_preset, request.custom_style, width=info.width, height=info.height)
                    duration = time.perf_counter() - t_step_start
                    steps[current] = StepStatus.COMPLETED
                    metrics.record_step(step=current.value, status="COMPLETED", duration=duration)
                    logger.info("Etapa %s concluída em %.2fs", current.value, duration)

                    pct, current = 70, JobStep.BURNING_SUBTITLES
                    steps[current] = StepStatus.RUNNING
                    t_step_start = time.perf_counter()
                    update()
                    output = destination or self.settings.output_dir / f"{job.job_id}.mp4"
                    output = self.renderer.render(request.video_file, ass, output)
                    duration = time.perf_counter() - t_step_start
                    steps[current] = StepStatus.COMPLETED
                    metrics.record_step(step=current.value, status="COMPLETED", duration=duration)
                    logger.info("Etapa %s concluída em %.2fs", current.value, duration)

                    pct = 100
                    total_duration = time.perf_counter() - t_job_start
                    metrics.job_finished()
                    metrics.record_job(
                        status="COMPLETED",
                        mode=request.transcription_mode.value,
                        preset=request.style_preset.value,
                        duration=total_duration,
                    )
                    logger.info("Job %s concluído com sucesso em %.2fs", job.job_id, total_duration)
                    return update(JobStatus.COMPLETED, output=output.resolve())
            except Exception as exc:
                total_duration = time.perf_counter() - t_job_start
                metrics.job_finished()
                if current and steps[current] == StepStatus.RUNNING:
                    steps[current] = StepStatus.FAILED
                    metrics.record_step(step=current.value, status="FAILED", duration=time.perf_counter() - t_step_start)
                error = str(exc) if isinstance(exc, (MediaError, SubtitleError, TranscriptionError)) else "Falha no processamento; consulte a configuração e os arquivos de entrada."
                metrics.record_job(
                    status="FAILED",
                    mode=request.transcription_mode.value,
                    preset=request.style_preset.value,
                    duration=total_duration,
                )
                logger.error("Job %s falhou na etapa %s: %s", job.job_id, current.value if current else "None", error)
                return update(JobStatus.FAILED, error=error)
