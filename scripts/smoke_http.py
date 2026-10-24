"""Exercitar um servidor HTTP real local, encerrando-o ao terminar."""

import argparse
import socket
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from video_subtitleler.api.app import create_app
from video_subtitleler.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--subtitles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        parser.error("O destino já existe.")
    with tempfile.TemporaryDirectory(prefix="http-", dir=args.output.parent) as folder:
        work = Path(folder)
        settings = Settings(_env_file=None, work_dir=work / "work", output_dir=work / "output", database_path=work / "jobs.sqlite3")
        config = uvicorn.Config(create_app(settings), log_level="error")
        server = uvicorn.Server(config)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started:
                    if time.monotonic() >= deadline or not thread.is_alive():
                        raise RuntimeError("Servidor HTTP não iniciou.")
                    time.sleep(0.05)
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
                    assert client.get("/docs").status_code == 200
                    with args.video.open("rb") as video, args.subtitles.open("rb") as subtitle:
                        response = client.post("/api/v1/subtitles/generate", files={"video_file": ("input.mp4", video, "video/mp4"), "external_subtitle_file": (args.subtitles.name, subtitle)}, data={"transcription_mode": "external", "style_preset": "instagram_music"})
                    response.raise_for_status()
                    assert response.status_code == 202
                    job_id = response.json()["job_id"]
                    states = []
                    deadline = time.monotonic() + 60
                    while time.monotonic() < deadline:
                        state = client.get(f"/api/v1/jobs/{job_id}").json()
                        if not states or states[-1] != state["status"]:
                            states.append(state["status"])
                        if state["status"] in {"COMPLETED", "FAILED"}:
                            break
                        time.sleep(0.05)
                    if state["status"] != "COMPLETED":
                        raise RuntimeError(f"Job HTTP não concluiu: {state['status']}")
                    download = client.get(f"/api/v1/jobs/{job_id}/download")
                    download.raise_for_status()
                    with args.output.open("xb") as output:
                        output.write(download.content)
                    print(f"POST 202; estados {states}; download {len(download.content)} bytes; /docs 200")
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                if thread.is_alive():
                    raise RuntimeError("Servidor não encerrou no prazo.")


if __name__ == "__main__":
    main()
