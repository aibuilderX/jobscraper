from datetime import datetime, timezone
import httpx
from langdetect import detect, LangDetectException
from ..models import Job


def parse_listing(data: dict, subreddit: str) -> list[Job]:
    jobs: list[Job] = []
    for child in data.get("data", {}).get("children", []):
        p = child.get("data", {})
        title = p.get("title", "") or ""
        if "[hiring]" not in title.lower():
            continue
        description = p.get("selftext", "") or ""
        text_sample = f"{title} {description}".strip()
        try:
            lang = detect(text_sample) if text_sample else "en"
        except LangDetectException:
            lang = "en"
        permalink = p.get("permalink", "")
        jobs.append(
            Job.make(
                source="reddit",
                external_id=p["id"],
                title=title[:200],
                description=description[:2000],
                budget_eur=None,
                language=lang,
                url=f"https://www.reddit.com{permalink}",
                posted_at=datetime.fromtimestamp(
                    p.get("created_utc", 0), tz=timezone.utc
                ),
                raw={"subreddit": subreddit},
            )
        )
    return jobs


async def fetch(subs: list[str]) -> list[Job]:
    jobs: list[Job] = []
    headers = {"User-Agent": "jobscraper/0.1"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as c:
        for sub in subs:
            try:
                r = await c.get(
                    f"https://www.reddit.com/r/{sub}/new.json?limit=25"
                )
                r.raise_for_status()
                jobs.extend(parse_listing(r.json(), subreddit=sub))
            except Exception:
                # non-fatal: one subreddit failing shouldn't drop the others
                continue
    return jobs
