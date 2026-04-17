import re
from datetime import datetime, timezone, timedelta
from selectolax.parser import HTMLParser
import httpx
from ..models import Job

BASE = "https://www.codeur.com"

_PROJECT_HREF_RE = re.compile(r"^/projects/(\d+)")
_BUDGET_RANGE_RE = re.compile(r"(\d{2,6})\s*(?:à|-|–)\s*(\d{2,6})\s*€")
_BUDGET_SINGLE_RE = re.compile(r"(\d{2,6})\s*€")
_BUDGET_LESS_RE = re.compile(r"Moins de", re.IGNORECASE)
_TIME_RE = re.compile(r"Il y a\s+(\d+)\s+(minute|heure|jour|mois)", re.IGNORECASE)


def _parse_budget(text: str) -> float | None:
    if _BUDGET_LESS_RE.search(text):
        return 0.0
    m = _BUDGET_RANGE_RE.search(text)
    if m:
        return float(m.group(1))
    m = _BUDGET_SINGLE_RE.search(text)
    if m:
        return float(m.group(1))
    return None


def _parse_time_ago(text: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    m = _TIME_RE.search(text)
    if not m:
        return now
    n = int(m.group(1))
    unit = m.group(2).lower()
    delta = {
        "minute": timedelta(minutes=n),
        "heure": timedelta(hours=n),
        "jour": timedelta(days=n),
        "mois": timedelta(days=30 * n),
    }.get(unit, timedelta(0))
    return now - delta


def parse_projects(html: str) -> list[Job]:
    tree = HTMLParser(html)
    jobs: dict[str, Job] = {}
    now = datetime.now(timezone.utc)

    for card in tree.css("a[href^='/projects/']"):
        href = card.attributes.get("href", "") or ""
        m = _PROJECT_HREF_RE.match(href)
        if not m:
            continue
        external_id = m.group(1)
        if external_id in jobs:
            continue  # de-dupe within a single page

        url = BASE + href
        divs = card.css("div")
        # Div 0: title + time-ago. Div 1: status/budget/offers. Div 2: description.
        title_block = divs[0].text(strip=True) if len(divs) > 0 else ""
        meta_block = divs[1].text(strip=True) if len(divs) > 1 else ""
        desc_block = divs[2].text(strip=True) if len(divs) > 2 else ""

        title = _TIME_RE.sub("", title_block).strip()
        budget = _parse_budget(meta_block)
        posted_at = _parse_time_ago(title_block, now=now)

        jobs[external_id] = Job.make(
            source="codeur",
            external_id=external_id,
            title=title[:200],
            description=desc_block[:2000],
            budget_eur=budget,
            language="fr",
            url=url,
            posted_at=posted_at,
            raw={"meta": meta_block},
        )
    return list(jobs.values())


async def fetch() -> list[Job]:
    async with httpx.AsyncClient(
        timeout=10, headers={"User-Agent": "Mozilla/5.0"}
    ) as c:
        r = await c.get(f"{BASE}/projects")
        r.raise_for_status()
        return parse_projects(r.text)
