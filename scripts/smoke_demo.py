"""Gerar amostras reais a partir de voz e pesos locais, sem downloads implícitos.

Uso: python scripts/smoke_demo.py --voice voz.wav --model caminho/modelo
"""

import argparse
import json
import tempfile
from pathlib import Path

from video_subtitleler.config import Settings
from video_subtitleler.models.schema import SubtitleRequest
from video_subtitleler.services.audio import AudioService, run_media
from video_subtitleler.services.ass_builder import ASSBuilder
from video_subtitleler.services.pipeline import Pipeline
from video_subtitleler.services.transcriber import Transcriber
from video_subtitleler.storage.job_store import SQLiteJobStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/demo"))
    args = parser.parse_args()
    if not args.voice.is_file() or not args.model.is_dir():
        parser.error("Informe voz existente e diretório de pesos locais.")
    args.output.mkdir(parents=True, exist_ok=True)
    # Unique run folder preserves previous samples.
    folder = Path(tempfile.mkdtemp(prefix="run-", dir=args.output)).resolve()
    settings = Settings(_env_file=None, whisper_model=str(args.model.resolve()), work_dir=folder / "work", output_dir=folder, database_path=folder / "jobs.sqlite3")
    video = folder / "input.mp4"
    run_media([settings.ffmpeg_path, "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=0x122033:s=1280x720:r=30", "-i", str(args.voice.resolve()), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(video)], 60)
    audio = AudioService(settings)
    transcriber = Transcriber(settings)
    wav = audio.extract(video, folder / "audio.wav")
    track = transcriber.transcribe(wav, "en")
    (folder / "transcript.json").write_text(track.model_dump_json(indent=2), encoding="utf-8")
    pipeline = Pipeline(settings, SQLiteJobStore(settings.database_path), transcriber=transcriber)
    evidence = {}
    for preset in ("movie_series", "instagram_music"):
        output = folder / f"{preset}.mp4"
        request = SubtitleRequest(video_file=video, style_preset=preset, language="en")
        result = pipeline.run(request, destination=output)
        if result.status != "COMPLETED":
            raise RuntimeError(result.progress.error)
        evidence[preset] = {"job_id": str(result.job_id), "output": str(output), "steps": result.progress.model_dump(mode="json")["steps"]}
        ASSBuilder().write(folder / f"{preset}.ass", track, preset, width=1280, height=720)
    # Exercise the real Whisper -> unconfigured LLM fallback -> renderer path.
    hybrid = pipeline.run(SubtitleRequest(video_file=video, transcription_mode="llm_hybrid", style_preset="instagram_music", language="en"), destination=folder / "hybrid_fallback.mp4")
    if hybrid.status != "COMPLETED" or hybrid.progress.steps["llm_enhancement"] != "SKIPPED":
        raise RuntimeError("O fallback híbrido não concluiu como esperado.")
    evidence["hybrid_fallback"] = {"status": hybrid.status, "steps": hybrid.progress.model_dump(mode="json")["steps"]}
    (folder / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(folder)


if __name__ == "__main__":
    main()
