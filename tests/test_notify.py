import respx
import httpx
from jobscraper.notify import send_job


@respx.mock
def test_send_job_posts_to_telegram(job_factory, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    route = respx.post("https://api.telegram.org/botT/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    job = job_factory(title="Landing page", url="https://ex.com/1")
    send_job(job, draft="Hi there.")
    assert route.called
    body = route.calls.last.request.content.decode()
    assert "Landing page" in body
    assert "Hi there." in body
    assert "https://ex.com/1" in body
    assert "42" in body
