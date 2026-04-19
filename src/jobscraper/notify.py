import os
import httpx
from .models import Job


def _esc(s: str) -> str:
    # strip chars that break Telegram Markdown
    return s.replace("*", "").replace("_", "").replace("`", "").replace("[", "(").replace("]", ")")


def send_job(job: Job, draft: str, build_cmd: str | None = None) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    budget_line = f"€{int(job.budget_eur)}" if job.budget_eur else "budget N/A"
    build_line = f"\n\n🛠 *Build preview:*\n`{build_cmd}`" if build_cmd else ""
    text = (
        f"💼 *{_esc(job.title)}*\n"
        f"_{job.source} · {job.language} · {budget_line}_\n\n"
        f"{_esc(job.description)[:400]}\n\n"
        f"🔗 {job.url}\n\n"
        f"✉️ *Draft:*\n{_esc(draft)}"
        f"{build_line}"
    )
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    r.raise_for_status()
