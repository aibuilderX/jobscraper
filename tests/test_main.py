from unittest.mock import patch, AsyncMock
from pathlib import Path
from datetime import datetime, timezone, timedelta
from jobscraper.main import run


def test_run_filters_dedupes_drafts_and_notifies(tmp_path, monkeypatch, job_factory):
    monkeypatch.setenv("ZAI_API_KEY", "x")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    state = tmp_path / "seen.json"
    cfg_path = Path("tests/fixtures/config_minimal.yaml")

    relevant = job_factory(
        external_id="fresh-1",
        title="React landing page",
        language="en",
    )
    stale = job_factory(
        external_id="old-1",
        posted_at=datetime.now(timezone.utc) - timedelta(days=2),
    )

    with patch("jobscraper.main.fetch_all", new=AsyncMock(return_value=[relevant, stale])), \
         patch("jobscraper.main.draft_pitch", return_value="Hi!"), \
         patch("jobscraper.main.get_client", return_value=object()), \
         patch("jobscraper.main.send_job") as send:
        run(config_path=cfg_path, state_path=state)
        assert send.call_count == 1
        sent_job = send.call_args.args[0]
        assert sent_job.id.endswith("fresh-1")

    # Second run: same job should now be deduped
    with patch("jobscraper.main.fetch_all", new=AsyncMock(return_value=[relevant])), \
         patch("jobscraper.main.draft_pitch", return_value="Hi!"), \
         patch("jobscraper.main.get_client", return_value=object()), \
         patch("jobscraper.main.send_job") as send:
        run(config_path=cfg_path, state_path=state)
        assert send.call_count == 0


def test_run_continues_when_draft_fails(tmp_path, monkeypatch, job_factory):
    monkeypatch.setenv("ZAI_API_KEY", "x")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    state = tmp_path / "seen.json"
    cfg_path = Path("tests/fixtures/config_minimal.yaml")

    job = job_factory(external_id="j1", title="React landing page", language="en")

    with patch("jobscraper.main.fetch_all", new=AsyncMock(return_value=[job])), \
         patch("jobscraper.main.draft_pitch", side_effect=RuntimeError("llm down")), \
         patch("jobscraper.main.get_client", return_value=object()), \
         patch("jobscraper.main.send_job") as send:
        run(config_path=cfg_path, state_path=state)
        assert send.call_count == 1
        # fallback draft message is sent
        assert "draft failed" in send.call_args.args[1].lower()
