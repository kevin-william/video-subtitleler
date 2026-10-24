"""Orquestração síncrona compartilhada pela CLI e worker HTTP."""

import tempfile
from pathlib import Path
from uuid import UUID

from video_subtitleler.config import Settings
from video_subtitleler.models.schema import JobProgress, JobStatus, JobStep, StepStatus, SubtitleRequest, TranscriptionMode
from video_subtitleler.storage.job_store import SQLiteJobStore
from .ass_builder import ASSBuilder
from .audio import AudioService, MediaError
from .external_subtitles import SubtitleError, load_external
from .llm_enhancer import LLMEnhancer
from .renderer import Renderer
from .transcriber import Transcriber, TranscriptionError


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

        def update(status=JobStatus.PROCESSING, *, error=None, output=None):
            progress = JobProgress(job_id=job.job_id, status=status, progress_pct=pct, current_step=current, steps=dict(steps), error=error)
            result = self.store.update(progress, output)
            if on_progress:
                on_progress(progress)
            return result

        update()
        try:
            info = self.audio.probe(request.video_file)
            self.settings.work_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=f"job-{job.job_id}-", dir=self.settings.work_dir) as folder:
                work = Path(folder)
                if request.transcription_mode == TranscriptionMode.EXTERNAL:
                    for step in (JobStep.EXTRACT_AUDIO, JobStep.TRANSCRIPTION, JobStep.LLM_ENHANCEMENT):
                        steps[step] = StepStatus.SKIPPED
                    track = self.external_loader(request.external_subtitle_file)
                else:
                    current = JobStep.EXTRACT_AUDIO
                    steps[current] = StepStatus.RUNNING
                    update()
                    wav = self.audio.extract(request.video_file, work / "audio.wav")
                    steps[current] = StepStatus.COMPLETED
                    pct, current = 20, JobStep.TRANSCRIPTION
                    steps[current] = StepStatus.RUNNING
                    update()
                    track = self.transcriber.transcribe(wav, request.language)
                    steps[current] = StepStatus.COMPLETED
                    pct = 50
                    if request.transcription_mode == TranscriptionMode.LLM_HYBRID:
                        current = JobStep.LLM_ENHANCEMENT
                        steps[current] = StepStatus.RUNNING
                        update()
                        original = track
                        track = self.enhancer.enhance_with_fallback(track, request.style_preset)
                        steps[current] = StepStatus.SKIPPED if track is original else StepStatus.COMPLETED
                    else:
                        steps[JobStep.LLM_ENHANCEMENT] = StepStatus.SKIPPED
                pct, current = 60, JobStep.GENERATE_ASS
                steps[current] = StepStatus.RUNNING
                update()
                ass = self.builder.write(work / "subtitles.ass", track, request.style_preset, request.custom_style, width=info.width, height=info.height)
                steps[current] = StepStatus.COMPLETED
                pct, current = 70, JobStep.BURNING_SUBTITLES
                steps[current] = StepStatus.RUNNING
                update()
                output = destination or self.settings.output_dir / f"{job.job_id}.mp4"
                output = self.renderer.render(request.video_file, ass, output)
                steps[current] = StepStatus.COMPLETED
                pct = 100
                return update(JobStatus.COMPLETED, output=output.resolve())
        except Exception as exc:
            if current and steps[current] == StepStatus.RUNNING:
                steps[current] = StepStatus.FAILED
            error = str(exc) if isinstance(exc, (MediaError, SubtitleError, TranscriptionError)) else "Falha no processamento; consulte a configuração e os arquivos de entrada."
            return update(JobStatus.FAILED, error=error)
