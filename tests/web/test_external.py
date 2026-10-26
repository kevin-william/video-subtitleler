import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.web_ui


def set_file(page, selector, name, content):
    page.locator(selector).set_input_files({"name": name, "mimeType": "application/octet-stream", "buffer": content})


def test_combined_limit_and_mode_cleanup(page, web_url, mock_job):
    submitted, _ = mock_job()
    page.route("**/api/v1/ui-config", lambda route: route.fulfill(json={"max_upload_bytes": 10}))
    page.goto(web_url)
    set_file(page, "#video-file", "vídeo com espaço.MP4", b"12345678")
    page.locator("#mode").select_option("external")
    set_file(page, "#external-file", "legenda.srt", b"123")
    expect(page.get_by_role("alert")).to_contain_text("somando vídeo e legenda")
    page.locator("#mode").select_option("whisper_only")
    expect(page.locator("#external-panel")).to_be_hidden()
    assert page.locator("#external-file").evaluate("e => e.files.length") == 0
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible()
    assert "external_subtitle_file" not in submitted[0].decode()


def test_conditional_validation(page, web_url):
    page.goto(web_url)
    set_file(page, "#video-file", "video.mp4", b"fixture")
    page.locator("#mode").select_option("external")
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text("Escolha o arquivo de legenda")
    set_file(page, "#external-file", "sub.txt", b"fixture")
    expect(page.get_by_role("alert")).to_contain_text("SRT, VTT ou JSON")
    set_file(page, "#external-file", "sub.srt", b"")
    expect(page.get_by_role("alert")).to_contain_text("está vazio")
    set_file(page, "#external-file", "sub.srt", b"fixture")
    page.locator('input[value="instagram_music"]').check()
    expect(page.get_by_role("alert")).to_contain_text("JSON com palavras alinhadas")


@pytest.mark.parametrize("preset", ["movie_series", "instagram_music"])
def test_real_external_browser_to_ffmpeg(page, real_web_url, video, track, preset):
    page.goto(real_web_url)
    page.locator("#video-file").set_input_files(video)
    page.locator("#mode").select_option("external")
    page.locator(f'input[value="{preset}"]').check()
    if preset == "movie_series":
        name, content = "legenda.srt", b"1\n00:00:00,100 --> 00:00:01,600\nHello world\n"
    else:
        name, content = "palavras.json", track.model_dump_json().encode()
    set_file(page, "#external-file", name, content)
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible(timeout=20000)
    with page.expect_download() as info:
        page.get_by_role("link", name="Baixar vídeo MP4").click()
    assert info.value.failure() is None
    assert info.value.path().stat().st_size > 1000


def test_json_extension_does_not_bypass_backend_alignment(page, real_web_url, video):
    page.goto(real_web_url)
    page.locator("#video-file").set_input_files(video)
    page.locator("#mode").select_option("external")
    page.locator('input[value="instagram_music"]').check()
    set_file(page, "#external-file", "invalid.json", b'{"language":"pt","segments":[{"text":"Hello","start":0.1,"end":1.0}]}')
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text("palavras alinhadas")
