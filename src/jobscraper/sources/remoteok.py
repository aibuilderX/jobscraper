from datetime import datetime, timezone
import httpx
from selectolax.parser import HTMLParser
from langdetect import detect, LangDetectException
from ..models import Job

# Approximate USD→EUR conversion. Fine-grained FX accuracy isn't needed:
# the budget filter has a single threshold, and RemoteOK salaries are
# annual-leaning ranges, not hourly gig prices. Update if rates drift sharply.
USD_TO_EUR = 0.92

API_URL = "https://remoteok.com/api"


def _strip_html(html: str) -> str:
    if not html:
        return ""
    tree = HTMLParser(html)
    return tree.text(separator=" ", strip=True)[:2000]


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def parse_listing(data: list[dict]) -> list[Job]:
    jobs: list[Job] = []
    for entry in data:
        # First element is the API legal notice, not a job
        if not entry.get("id") or not entry.get("position"):
            continue
        description = _strip_html(entry.get("description") or "")
        title = (entry.get("position") or "")[:200]
        company = entry.get("company") or ""
        text_sample = f"{title} {description}".strip()
        try:
            lang = detect(text_sample) if text_sample else "en"
        except LangDetectException:
            lang = "en"
        salary_min = entry.get("salary_min") or 0
        budget_eur: float | None = (
            float(salary_min) * USD_TO_EUR if salary_min and salary_min > 0 else None
        )
        jobs.append(
            Job.make(
                source="remoteok",
                external_id=str(entry["id"]),
                title=title,
                description=f"{company} · {description}" if company else description,
                budget_eur=budget_eur,
                language=lang,
                url=entry.get("url", ""),
                posted_at=_parse_date(entry.get("date")),
                raw={
                    "tags": entry.get("tags", []),
                    "company": company,
                    "apply_url": entry.get("apply_url"),
                },
            )
        )
    return jobs


async def fetch() -> list[Job]:
    headers = {"User-Agent": "jobscraper/0.1"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as c:
        r = await c.get(API_URL)
        r.raise_for_status()
        return parse_listing(r.json())
