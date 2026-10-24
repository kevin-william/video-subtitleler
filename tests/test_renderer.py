import pytest

from video_subtitleler.services.ass_builder import ASSBuilder
from video_subtitleler.services.audio import AudioService, MediaError
from video_subtitleler.services.renderer import Renderer


@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_real_render_with_windows_paths(settings, video, track, tmp_path, preset):
    ass = ASSBuilder().write(tmp_path / "sub 'á'.ass", track, preset, width=640, height=360)
    output = tmp_path / f"resultado com 'á' {preset}.mp4"
    assert Renderer(settings).render(video, ass, output) == output.resolve()
    info = AudioService(settings).probe(output)
    assert info.has_audio and (info.width, info.height) == (640, 360)
    assert video.exists()
    assert not list(tmp_path.glob("render-*"))
    with pytest.raises(MediaError):
        Renderer(settings).render(video, ass, output)


def test_renderer_failure_preserves_input_and_existing_output(settings, video, track, tmp_path):
    ass = ASSBuilder().write(tmp_path / "sub.ass", track, "movie_series")
    with pytest.raises(MediaError):
        Renderer(settings).render(video, ass, video)
    bad = settings.model_copy(update={"ffmpeg_path": "nonexistent-ffmpeg-command"})
    output = tmp_path / "out.mp4"
    with pytest.raises(MediaError):
        Renderer(bad).render(video, ass, output)
    assert video.exists() and not output.exists()


def test_real_highlight_moves_and_disappears_during_pause(settings, video, track, tmp_path):
    import subprocess
    ass = ASSBuilder().write(tmp_path / "karaoke.ass", track, "instagram_music", width=640, height=360)
    output = Renderer(settings).render(video, ass, tmp_path / "karaoke.mp4")
    centers = []
    for when in (0.3, 0.8, 1.2):
        result = subprocess.run([settings.ffmpeg_path, "-nostdin", "-v", "error", "-ss", str(when), "-i", str(output), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], capture_output=True, timeout=30, check=True)
        data = result.stdout
        x = [i // 3 % 640 for i in range(0, len(data), 3) if data[i] < 80 and data[i + 1] > 170 and data[i + 2] > 100]
        centers.append(sum(x) / len(x) if x else None)
    assert centers[0] is not None and centers[2] is not None
    assert centers[1] is None
    assert centers[0] < centers[2]
