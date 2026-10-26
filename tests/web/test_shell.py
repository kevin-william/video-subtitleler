import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.web_ui


def test_shell_uses_local_assets(page, web_url):
    urls = []
    page.on("request", lambda request: urls.append(request.url))
    page.goto(web_url)
    expect(page.get_by_role("heading", name="Cada palavra, no seu tempo.")).to_be_visible()
    expect(page.get_by_text("Serviço conectado", exact=True)).to_be_visible()
    assert all(url.startswith(web_url) for url in urls)
    page.set_viewport_size({"width": 360, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_config_failure_can_retry(page, web_url):
    page.route("**/api/v1/ui-config", lambda route: route.fulfill(status=503, json={"detail": "unavailable"}))
    page.goto(web_url)
    expect(page.get_by_text("Serviço indisponível", exact=True)).to_be_visible()
    page.unroute("**/api/v1/ui-config")
    page.get_by_role("button", name="Tentar novamente").click()
    expect(page.get_by_text("Serviço conectado", exact=True)).to_be_visible()
