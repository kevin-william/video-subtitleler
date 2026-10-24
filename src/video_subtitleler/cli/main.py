import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.progress import Progress

from video_subtitleler.config import Settings
from video_subtitleler.models.schema import CustomStyle, JobStatus, StylePreset, SubtitleRequest, TranscriptionMode
from video_subtitleler.services.pipeline import Pipeline

app = typer.Typer(no_args_is_help=True, help="Gerar legendas e gravá-las em um vídeo MP4.")
console = Console()


@app.callback()
def main():
    pass


def make_pipeline():
    return Pipeline(Settings())


@app.command()
def process(
    video: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    transcription_mode: Annotated[TranscriptionMode, typer.Option("--transcription-mode")] = TranscriptionMode.WHISPER_ONLY,
    style: Annotated[StylePreset, typer.Option("--style")] = StylePreset.MOVIE_SERIES,
    external_subtitle: Annotated[Path | None, typer.Option("--external-subtitle", exists=True, dir_okay=False)] = None,
    language: str = "auto",
    custom_style: Annotated[str, typer.Option(help="Objeto JSON com overrides de estilo.")] = "{}",
):
    try:
        request = SubtitleRequest(video_file=video, transcription_mode=transcription_mode, style_preset=style, external_subtitle_file=external_subtitle, language=language, custom_style=CustomStyle.model_validate(json.loads(custom_style)))
    except (ValidationError, ValueError):
        console.print("[red]Parâmetros inválidos. Confira modo, legenda externa e JSON de estilo.[/red]")
        raise typer.Exit(2)
    try:
        pipeline = make_pipeline()
        with Progress(console=console) as progress:
            task = progress.add_task("Processando", total=100)

            def notify(state):
                progress.update(task, completed=state.progress_pct, description=state.current_step or state.status)

            result = pipeline.run(request, destination=output, on_progress=notify)
        if result.status != JobStatus.COMPLETED:
            console.print(result.progress.error, style="red", markup=False)
            raise typer.Exit(1)
        console.print(f"Vídeo legendado: {result.output_path}", markup=False)
    except typer.Exit:
        raise
    except Exception:
        console.print("Falha ao iniciar o processamento. Confira a configuração e os diretórios.", markup=False)
        raise typer.Exit(1)
