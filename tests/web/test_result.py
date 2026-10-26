import json
import subprocess

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.web_ui


def send_external(page, url, video, track, preset="movie_series"):
    page.goto(url)
    page.locator("#video-file").set_input_files(video)
    page.locator("#mode").select_option("external")
    page.locator(f'input[value="{preset}"]').check()
    page.locator("#external-file").set_input_files({"name": "words.json", "mimeType": "application/json", "buffer": track.model_dump_json().encode()})
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible(timeout=20000)


@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_real_player_seek_range_and_download(page, real_web_url, video, track, preset, tmp_path):
    send_external(page, real_web_url, video, track, preset)
    player = page.locator("#result-video")
    page.wait_for_function("document.querySelector('#result-video').readyState >= 1", timeout=10000)
    assert player.evaluate("v => v.duration") > 1.5
    player.evaluate("async v => {v.muted=true;await v.play();}")
    page.wait_for_function("document.querySelector('#result-video').currentTime > 0.05")
    player.evaluate("v => {v.pause();v.currentTime = 1;}")
    page.wait_for_function("Math.abs(document.querySelector('#result-video').currentTime-1) < 0.15")
    url = player.get_attribute("src")
    partial = page.request.get(real_web_url + url, headers={"Range": "bytes=0-99"})
    assert partial.status == 206
    assert len(partial.body()) == 100
    assert partial.headers["content-type"] == "video/mp4"
    with page.expect_download() as info:
        page.get_by_role("link", name="Baixar vídeo MP4").click()
    destination = tmp_path / "download.mp4"
    info.value.save_as(destination)
    media = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "json", str(destination)]))
    assert media["streams"][0]["codec_name"] == "h264"
    assert media["streams"][1]["codec_name"] == "aac"
    assert destination.stat().st_size > 1000


def test_second_cycle_resets_files_style_and_focus(page, real_web_url, video, track):
    send_external(page, real_web_url, video, track)
    old_src = page.locator("#result-video").get_attribute("src")
    page.get_by_role("button", name="Processar novo vídeo").click()
    expect(page.locator("#result-view")).to_be_hidden()
    assert page.locator("#result-video").get_attribute("src") is None
    assert page.locator("#video-file").evaluate("e=>e.files.length") == 0
    assert page.locator("#external-file").evaluate("e=>e.files.length") == 0
    expect(page.locator("#mode")).to_have_value("whisper_only")
    expect(page.locator("#choose-file")).to_be_focused()
    expect(page.locator('[data-style="font_size"]')).to_have_value("")
    page.locator("#video-file").set_input_files(video)
    page.locator("#mode").select_option("external")
    page.locator("#external-file").set_input_files({"name": "second.json", "mimeType": "application/json", "buffer": track.model_dump_json().encode()})
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible(timeout=20000)
    assert page.locator("#result-video").get_attribute("src") != old_src


def test_player_error_preserves_download(page, web_url, mock_job):
    _, job_id = mock_job()
    page.route(f"**/api/v1/jobs/{job_id}/download", lambda route: route.fulfill(status=404, json={"detail": "missing"}))
    page.goto(web_url)
    page.locator("#video-file").set_input_files({"name": "video.mp4", "mimeType": "video/mp4", "buffer": b"fixture"})
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#media-error")).to_be_visible()
    expect(page.get_by_role("link", name="Baixar vídeo MP4")).to_have_attribute("href", f"/api/v1/jobs/{job_id}/download")


def test_hybrid_fallback_is_explained_in_result(page, web_url, mock_job):
    keys = ["extract_audio", "transcription", "llm_enhancement", "generate_ass", "burning_subtitles"]
    mock_job(steps={key: "SKIPPED" if key == "llm_enhancement" else "COMPLETED" for key in keys})
    page.goto(web_url)
    page.locator("#video-file").set_input_files({"name": "video.mp4", "mimeType": "video/mp4", "buffer": b"fixture"})
    page.locator("#mode").select_option("llm_hybrid")
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#refinement-note")).to_be_visible()
    page.get_by_role("button", name="Processar novo vídeo").click()
    expect(page.locator("#refinement-note")).to_be_hidden()


@pytest.mark.parametrize("width", [360, 1280])
def test_responsive_form_result_and_reduced_motion(page, web_url, mock_job, width):
    mock_job()
    page.set_viewport_size({"width": width, "height": 900})
    page.emulate_media(reduced_motion="reduce")
    page.goto(web_url)
    page.locator("#advanced-style summary").click()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#video-file").set_input_files({"name": "video.mp4", "mimeType": "video/mp4", "buffer": b"fixture"})
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible()
    expect(page.locator("#result-title")).to_be_focused()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator("#progress-fill").evaluate("e => getComputedStyle(e).transitionDuration") == "0s"
