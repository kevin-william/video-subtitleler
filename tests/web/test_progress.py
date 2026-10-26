import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.web_ui
ID = "00000000-0000-4000-8000-000000000001"
STEPS = ["extract_audio", "transcription", "llm_enhancement", "generate_ass", "burning_subtitles"]


def progress(status="PROCESSING", percentage=20, steps=None, current="transcription"):
    return {"job_id": ID, "status": status, "progress_pct": percentage, "steps": steps or {key: "PENDING" for key in STEPS}, "current_step": current, "error": None}


def begin(page, url):
    page.clock.install()
    page.goto(url)
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    page.locator("#video-file").set_input_files({"name": "video.mp4", "mimeType": "video/mp4", "buffer": b"fixture"})
    page.get_by_role("button", name="Gerar legendas").click()


def test_stepper_and_terminal_stop(page, web_url, mock_job):
    mock_job()
    calls = []
    states = [progress("QUEUED", 0, current=None), progress(steps={key: state for key, state in zip(STEPS, ["COMPLETED", "RUNNING", "SKIPPED", "PENDING", "PENDING"])}), progress("COMPLETED", 100, {key: "COMPLETED" for key in STEPS}, "burning_subtitles")]

    def get(route):
        calls.append(1)
        route.fulfill(json=states.pop(0))

    page.route(f"**/api/v1/jobs/{ID}", get)
    begin(page, web_url)
    expect(page.locator("#job-description")).to_have_text("Seu vídeo está na fila.")
    page.clock.run_for(1500)
    expect(page.locator('[data-step="transcription"]')).to_have_attribute("aria-current", "step")
    expect(page.locator('[data-step="llm_enhancement"]')).to_contain_text("Dispensada")
    expect(page.get_by_role("progressbar")).to_have_attribute("aria-valuenow", "20")
    page.clock.run_for(1500)
    expect(page.locator("#result-view")).to_be_visible()
    page.clock.run_for(60000)
    assert len(calls) == 3


def test_transient_recovery_exhausts_then_resumes_same_job(page, web_url, mock_job):
    submitted, _ = mock_job()
    calls = []

    def get(route):
        calls.append(1)
        if len(calls) <= 4:
            route.fulfill(status=503, json={"detail": "temporário"})
        else:
            route.fulfill(json=progress("COMPLETED", 100, {key: "COMPLETED" for key in STEPS}))

    page.route(f"**/api/v1/jobs/{ID}", get)
    begin(page, web_url)
    for attempt, delay in [(1, 1500), (2, 3000), (3, 6000)]:
        expect(page.locator("#poll-notice")).to_contain_text(f"{attempt}/3")
        page.clock.run_for(delay)
    expect(page.get_by_role("button", name="Retomar acompanhamento")).to_be_visible()
    expect(page.locator("#job-error")).to_contain_text("pausado")
    page.get_by_role("button", name="Retomar acompanhamento").click()
    expect(page.locator("#result-view")).to_be_visible()
    assert len(submitted) == 1 and len(calls) == 5


@pytest.mark.parametrize("kind", ["missing", "invalid_json", "invalid_progress"])
def test_missing_or_invalid_job_response(page, web_url, mock_job, kind):
    mock_job()

    def get(route):
        if kind == "missing":
            route.fulfill(status=404, json={"detail": "missing"})
        elif kind == "invalid_json":
            route.fulfill(body="not json", content_type="application/json")
        else:
            route.fulfill(json=progress(percentage=999))

    page.route(f"**/api/v1/jobs/{ID}", get)
    begin(page, web_url)
    expect(page.locator("#job-error")).to_be_visible()
    if kind == "missing":
        expect(page.locator("#job-error")).to_contain_text("Processamento não encontrado")
        expect(page.locator("#resume-job")).to_be_hidden()
    else:
        expect(page.locator("#resume-job")).to_be_visible()
    expect(page.locator("#result-view")).to_be_hidden()


def test_slow_request_does_not_overlap_and_times_out(page, web_url, mock_job):
    mock_job()
    pending = []
    page.route(f"**/api/v1/jobs/{ID}", lambda route: pending.append(route))
    begin(page, web_url)
    expect(page.locator("#progress-view")).to_be_visible()
    page.wait_for_function("document.querySelector('#progress-view').hidden === false")
    page.clock.run_for(9000)
    assert len(pending) == 1
    page.clock.run_for(1001)
    expect(page.locator("#poll-notice")).to_contain_text("1/3")
    assert len(pending) == 1


def test_monitor_discards_response_from_previous_generation(page, web_url):
    page.goto(web_url)
    ids = [ID, "00000000-0000-4000-8000-000000000002"]
    pending = []
    page.route(f"**/api/v1/jobs/{ids[0]}", lambda route: pending.append(route))
    latest = progress("COMPLETED", 100, {key: "COMPLETED" for key in STEPS})
    latest["job_id"] = ids[1]
    page.route(f"**/api/v1/jobs/{ids[1]}", lambda route: route.fulfill(json=latest))
    page.evaluate("""async id => {
        const {JobMonitor} = await import('/static/job-monitor.js');
        window.updates = []; window.probeMonitor = new JobMonitor(v => window.updates.push(v.job_id), () => {});
        window.probeMonitor.start(id);
    }""", ids[0])
    page.wait_for_timeout(50)
    page.evaluate("id => window.probeMonitor.start(id)", ids[1])
    page.wait_for_function("window.updates.length === 1")
    for route in pending:
        route.fulfill(json=progress("COMPLETED", 100, {key: "COMPLETED" for key in STEPS}))
    assert page.evaluate("window.updates") == [ids[1]]


@pytest.mark.parametrize("body", ["null", '{"job_id":"not-a-uuid"}'])
def test_invalid_acceptance_never_starts_polling(page, web_url, body):
    page.route("**/api/v1/subtitles/generate", lambda route: route.fulfill(status=202, content_type="application/json", body=body))
    begin(page, web_url)
    expect(page.locator("#form-error")).to_be_visible()
    expect(page.locator("#progress-view")).to_be_hidden()
