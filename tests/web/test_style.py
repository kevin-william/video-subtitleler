import pytest
from playwright.sync_api import expect

from video_subtitleler.models.schema import CustomStyle
from .helpers import custom_style

pytestmark = pytest.mark.web_ui


@pytest.fixture
def style_page(page, web_url):
    submitted = []

    def post(route):
        submitted.append(route.request.post_data_buffer)
        route.fulfill(status=422, json={"detail": "capturado pelo teste"})

    page.route("**/api/v1/subtitles/generate", post)
    page.goto(web_url)
    page.locator("#video-file").set_input_files({"name": "video.mp4", "mimeType": "video/mp4", "buffer": b"fixture"})
    page.locator("#advanced-style summary").click()
    return submitted


@pytest.mark.parametrize("field,min_value,max_value,invalid", [
    ("font_size", 8, 200, "7"), ("inactive_opacity", 0, 1, "1.1"),
    ("margin_vertical", 0, 4096, "4097"), ("cpl", 37, 42, "36"),
])
def test_numeric_bounds_serialize_as_numbers(page, style_page, field, min_value, max_value, invalid):
    target = page.locator(f'[data-style="{field}"]')
    button = page.get_by_role("button", name="Gerar legendas")
    for value in [min_value, max_value]:
        target.fill(str(value))
        button.click()
        expect(page.get_by_role("alert")).to_contain_text("capturado")
        data = custom_style(style_page[-1])
        assert data == {field: value}
        CustomStyle.model_validate(data)
    target.fill(invalid)
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("entre")
    assert len(style_page) == 2


def test_defaults_restore_and_explicit_overrides_survive_preset(page, style_page):
    button = page.get_by_role("button", name="Gerar legendas")
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("capturado")
    assert custom_style(style_page[-1]) == {}
    page.locator('[data-style="font_size"]').fill("48")
    page.locator('[data-style="active_color"]').fill("#ffaa00")
    page.get_by_role("radio", name="Superior direita").check()
    page.locator('input[value="instagram_music"]').check()
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("capturado")
    assert custom_style(style_page[-1]) == {"font_size": 48, "active_color": "#FFAA00", "alignment": 9}
    page.get_by_role("button", name="Restaurar estilo padrão").click()
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("capturado")
    assert custom_style(style_page[-1]) == {}


def test_invalid_colors_fonts_and_decimal_integer(page, style_page):
    button = page.get_by_role("button", name="Gerar legendas")
    page.locator('[data-style="active_color"]').fill("#zzz000")
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("#RRGGBB")
    page.locator('[data-style="active_color"]').fill("")
    page.locator('[data-style="font_name"]').fill("Arial{unsafe}")
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("não permitidos")
    page.locator('[data-style="font_name"]').fill("")
    page.locator('[data-style="font_size"]').fill("8.5")
    button.click()
    expect(page.get_by_role("alert")).to_contain_text("inteiro")
    assert not style_page


def test_controls_are_synchronized(page, style_page):
    page.locator('[data-style="active_color"]').fill("#123456")
    expect(page.locator("#picker-active")).to_have_value("#123456")
    page.locator('[data-range="font_size"]').evaluate("e => {e.value='64';e.dispatchEvent(new Event('input',{bubbles:true}));}")
    expect(page.locator('[data-style="font_size"]')).to_have_value("64")
    page.get_by_role("button", name="Gerar legendas").click()
    expect(page.get_by_role("alert")).to_contain_text("capturado")
    assert custom_style(style_page[-1]) == {"active_color": "#123456", "font_size": 64}
