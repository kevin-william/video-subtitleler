import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.web_ui


def upload(page, name="video.MP4", content=b"synthetic-fixture"):
    page.locator("#video-file").set_input_files({"name": name, "mimeType": "video/mp4", "buffer": content})


def test_real_controlled_pipeline_cycle(page, fake_web_url, fake_pipeline):
    page.goto(fake_web_url)
    upload(page)
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible()
    with page.expect_download() as info:
        page.get_by_role("link", name="Baixar vídeo MP4").click()
    assert info.value.failure() is None
    assert fake_pipeline.calls == ["extract", "transcribe", "render"]


def test_payload_hybrid_and_manual_language(page, web_url, mock_job):
    submitted, job_id = mock_job()
    page.goto(web_url)
    upload(page)
    page.locator("#mode").select_option("llm_hybrid")
    page.locator("#language").select_option("custom")
    page.locator("#custom-language").fill("fr")
    page.locator('input[value="instagram_music"]').check()
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible()
    body = submitted[0].decode()
    for value in ["llm_hybrid", "instagram_music", "fr", "{}"]:
        assert value in body
    assert "external_subtitle_file" not in body
    assert len(submitted) == 1
    expect(page.locator("#download-link")).to_have_attribute("href", f"/api/v1/jobs/{job_id}/download")


@pytest.mark.parametrize("name,content,message", [
    ("video.txt", b"a", "formato MP4"), ("video.mp4", b"", "está vazio"),
])
def test_invalid_file(page, web_url, name, content, message):
    page.goto(web_url)
    upload(page, name, content)
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text(message)


def test_size_limit_and_invalid_language(page, web_url, mock_job):
    page.route("**/api/v1/ui-config", lambda route: route.fulfill(json={"max_upload_bytes": 10}))
    mock_job()
    page.goto(web_url)
    upload(page, content=b"a" * 11)
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text("limite")
    upload(page, content=b"a" * 10)
    page.locator("#language").select_option("custom")
    page.locator("#custom-language").fill("PT")
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text("minúsculas")
    page.locator("#custom-language").fill("pt")
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#result-view")).to_be_visible()


@pytest.mark.parametrize("status,detail,text", [
    (413, "large", "limite"), (422, [{"msg": "Parâmetro incorreto"}], "Parâmetro incorreto"),
    (422, "Vídeo inválido", "Vídeo inválido"), (500, "Serviço temporariamente indisponível", "indisponível"),
])
def test_post_error_keeps_form(page, web_url, status, detail, text):
    page.route("**/api/v1/subtitles/generate", lambda route: route.fulfill(status=status, json={"detail": detail}))
    page.goto(web_url)
    upload(page)
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text(text)
    expect(page.locator("#file-name")).to_have_text("video.MP4")
    expect(page.get_by_role("button", name="Gerar legendas")).to_be_enabled()


def test_drop_and_no_automatic_post_retry(page, web_url):
    posts = []
    page.route("**/api/v1/subtitles/generate", lambda route: (posts.append(1), route.abort()))
    page.goto(web_url)
    page.locator("#dropzone").evaluate("""element => {
        const dt = new DataTransfer(); dt.items.add(new File(['fixture'], 'arrastado.mp4'));
        element.dispatchEvent(new DragEvent('drop', {bubbles: true, dataTransfer: dt}));
    }""")
    expect(page.locator("#file-name")).to_have_text("arrastado.mp4")
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text("não será repetido")
    assert len(posts) == 1


def test_failed_job_is_text_not_html(page, web_url, mock_job):
    mock_job(status="FAILED", progress=20, error="<b>Falha no vídeo</b>")
    page.goto(web_url)
    upload(page)
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.locator("#job-error")).to_have_text("<b>Falha no vídeo</b>")
    assert page.locator("#job-error b").count() == 0
    expect(page.locator("#result-view")).to_be_hidden()
