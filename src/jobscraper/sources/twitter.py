import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
import httpx
from langdetect import detect, LangDetectException
from ..models import Job

NITTER_BASES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]


def parse_rss(xml: str, query: str) -> list[Job]:
    root = ET.fromstring(xml)
    jobs: list[Job] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = item.findtext("pubDate")
        try:
            posted = parsedate_to_datetime(pub) if pub else datetime.now(timezone.utc)
        except (TypeError, ValueError):
            posted = datetime.now(timezone.utc)
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        sample = f"{title} {desc}".strip()
        try:
            lang = detect(sample) if sample else "en"
        except LangDetectException:
            lang = "en"
        external_id = hashlib.sha1(link.encode()).hexdigest()[:12]
        jobs.append(
            Job.make(
                source="twitter",
                external_id=external_id,
                title=title[:200],
                description=desc[:2000],
                budget_eur=None,
                language=lang,
                url=link,
                posted_at=posted,
                raw={"query": query},
            )
        )
    return jobs


async def fetch(queries: list[str]) -> list[Job]:
    jobs: list[Job] = []
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(
        timeout=10, follow_redirects=True, headers=headers
    ) as c:
        for q in queries:
            for base in NITTER_BASES:
                try:
                    r = await c.get(
                        f"{base}/search/rss",
                        params={"f": "tweets", "q": q},
                    )
                    r.raise_for_status()
                    jobs.extend(parse_rss(r.text, query=q))
                    break
                except Exception:
                    continue
    return jobs
