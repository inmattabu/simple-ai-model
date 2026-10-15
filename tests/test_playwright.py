import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect


@pytest.fixture(scope="session")
def app_url():
    project_root = Path(__file__).resolve().parents[1]
    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        port = port_socket.getsockname()[1]

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 20

    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(f"FastAPI test server exited with status {process.returncode}")
        try:
            with urlopen(f"{base_url}/health", timeout=1):
                break
        except URLError:
            time.sleep(0.1)
    else:
        process.terminate()
        pytest.fail("FastAPI test server did not become ready")

    yield base_url

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def test_chat_submission_is_accessible_and_renders_mocked_reply(page, app_url):
    requests = []

    def mock_chat(route):
        requests.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"reply": "Mocked answer."}),
        )

    page.route("**/api/chat", mock_chat)
    page.goto(f"{app_url}/")

    message_input = page.get_by_role("textbox", name="Type your message")
    send_button = page.get_by_role("button", name="Send")
    expect(page.locator("#chat-window")).to_have_attribute("aria-live", "polite")
    expect(page.locator(".message.bot").first).to_have_text("Hello! Ask me anything.")

    message_input.focus()
    page.keyboard.type("How does this work?")
    page.keyboard.press("Tab")
    expect(send_button).to_be_focused()
    page.keyboard.press("Enter")

    expect(page.locator(".message.user").last).to_have_text("How does this work?")
    expect(page.locator(".message.bot").last).to_have_text("Mocked answer.")
    expect(message_input).to_have_value("")
    assert requests == [
        {
            "message": "How does this work?",
            "history": [{"role": "assistant", "content": "Hello! Ask me anything."}],
        }
    ]


def test_empty_and_whitespace_messages_are_not_submitted(page, app_url):
    requests = []
    page.route("**/api/chat", lambda route: requests.append(route.request.post_data_json))
    page.goto(f"{app_url}/")

    message_input = page.get_by_role("textbox", name="Type your message")
    send_button = page.get_by_role("button", name="Send")

    for message in ("", "   "):
        message_input.fill(message)
        send_button.click()
        expect(page.locator(".message")).to_have_count(1)

    assert requests == []


@pytest.mark.parametrize(
    "viewport",
    [{"width": 1280, "height": 800}, {"width": 375, "height": 812}],
    ids=["desktop", "mobile"],
)
def test_chat_controls_fit_viewport(page, app_url, viewport):
    page.set_viewport_size(viewport)
    page.goto(f"{app_url}/")

    expect(page.get_by_role("textbox", name="Type your message")).to_be_visible()
    expect(page.get_by_role("button", name="Send")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")