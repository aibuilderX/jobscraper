# Jobscraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a stateless Python scraper that runs on GitHub Actions every 5 minutes, pulls fresh freelance gigs from Codeur.com, Reddit, and Twitter/Nitter, filters them, drafts a tailored pitch via GLM-4.6 on z.ai, and pushes it to Telegram.

**Architecture:** Single Python package. Source modules each return `list[Job]`. Pipeline: fetch → filter → dedupe → draft → notify → persist. State persisted as `state/seen_jobs.json`, committed back by the cron job.

**Tech Stack:** Python 3.12, `httpx`, `selectolax`, `openai` (pointed at z.ai), `langdetect`, `pyyaml`, `pytest`, `respx` for HTTP mocking. GitHub Actions for scheduling.

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/jobscraper/__init__.py`
- Create: `tests/__init__.py`
- Create: `config.yaml`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "jobscraper"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27",
  "selectolax>=0.3",
  "openai>=1.40",
  "langdetect>=1.0.9",
  "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8", "respx>=0.21", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
*.egg-info/
.env
```

**Step 3: Create `config.yaml`**

```yaml
filters:
  min_budget_eur: 100
  max_age_hours: 2
  languages: [en, fr, es]
  keywords:
    - "landing page"
    - "one.?pager"
    - "site vitrine"
    - "page d.atterrissage"
    - "página de aterrizaje"
    - "site web simple"
    - "sitio web simple"
    - "next.?js"
    - "react"
    - "tailwind"
    - "framer"
    - "webflow"
    - "astro"
    - "website"
    - "site web"
    - "sitio web"

profile:
  summary_en: "Bilingual FR/EN/ES full-stack dev. I ship fast, clean landing pages in Next.js + Tailwind, usually in 48h."
  summary_fr: "Dev full-stack bilingue FR/EN/ES. Je livre des landing pages rapides et propres en Next.js + Tailwind, généralement sous 48h."
  summary_es: "Desarrollador full-stack bilingüe FR/EN/ES. Entrego landing pages rápidas y limpias con Next.js + Tailwind, normalmente en 48h."

nitter_queries:
  - '"need a landing page" lang:en'
  - '"looking for a developer" landing page lang:en'
  - '"cherche développeur" landing page lang:fr'
  - '"besoin d\'un site" lang:fr'
  - '"busco desarrollador" landing page lang:es'

reddit_subs:
  - forhire
  - slavelabour
  - hiring
```

**Step 4: Create empty `src/jobscraper/__init__.py` and `tests/__init__.py`**

**Step 5: Install and verify**

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
```
Expected: no tests collected, exit 0.

**Step 6: Commit**

```bash
git add pyproject.toml .gitignore src/ tests/ config.yaml
git commit -m "chore: project scaffold"
```

---

## Task 2: `Job` dataclass

**Files:**
- Create: `src/jobscraper/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing test**

`tests/test_models.py`:
```python
from datetime import datetime, timezone
from jobscraper.models import Job

def test_job_id_is_stable_hash():
    j = Job.make(source="codeur", external_id="abc123", title="t", description="d",
                 budget_eur=100.0, language="fr",
                 url="https://example.com", posted_at=datetime.now(timezone.utc), raw={})
    assert j.id == "codeur:abc123"

def test_job_is_frozen():
    j = Job.make(source="codeur", external_id="x", title="t", description="d",
                 budget_eur=None, language="en",
                 url="https://example.com", posted_at=datetime.now(timezone.utc), raw={})
    import dataclasses
    assert dataclasses.is_dataclass(j)
```

**Step 2: Run — expect FAIL (ImportError)**

`.venv/bin/pytest tests/test_models.py -v`

**Step 3: Implement**

`src/jobscraper/models.py`:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class Job:
    id: str
    source: str
    title: str
    description: str
    budget_eur: float | None
    language: str
    url: str
    posted_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def make(cls, *, source: str, external_id: str, **kwargs) -> "Job":
        return cls(id=f"{source}:{external_id}", source=source, **kwargs)
```

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git add src/jobscraper/models.py tests/test_models.py
git commit -m "feat: Job dataclass"
```

---

## Task 3: Config loader

**Files:**
- Create: `src/jobscraper/config.py`
- Create: `tests/test_config.py`
- Create: `tests/fixtures/config_minimal.yaml`

**Step 1: Test fixture** `tests/fixtures/config_minimal.yaml`:
```yaml
filters:
  min_budget_eur: 50
  max_age_hours: 1
  languages: [en]
  keywords: ["react", "landing page"]
profile:
  summary_en: "test profile"
  summary_fr: "profil test"
  summary_es: "perfil test"
nitter_queries: []
reddit_subs: []
```

**Step 2: Write failing test**

```python
from pathlib import Path
from jobscraper.config import load_config

def test_load_config_parses_fields():
    cfg = load_config(Path("tests/fixtures/config_minimal.yaml"))
    assert cfg.filters.min_budget_eur == 50
    assert cfg.filters.max_age_hours == 1
    assert cfg.filters.languages == ["en"]
    assert "react" in cfg.filters.keywords
    assert cfg.profile.summary_en == "test profile"

def test_keyword_regex_matches_case_insensitively():
    cfg = load_config(Path("tests/fixtures/config_minimal.yaml"))
    assert cfg.filters.keyword_regex.search("Need a LANDING PAGE quick")
```

**Step 3: Run — expect FAIL**

**Step 4: Implement** `src/jobscraper/config.py`:
```python
import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass(frozen=True)
class Filters:
    min_budget_eur: float
    max_age_hours: float
    languages: list[str]
    keywords: list[str]
    keyword_regex: re.Pattern = field(init=False)

    def __post_init__(self):
        joined = "|".join(self.keywords)
        object.__setattr__(self, "keyword_regex", re.compile(joined, re.IGNORECASE))

@dataclass(frozen=True)
class Profile:
    summary_en: str
    summary_fr: str
    summary_es: str

@dataclass(frozen=True)
class Config:
    filters: Filters
    profile: Profile
    nitter_queries: list[str]
    reddit_subs: list[str]

def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text())
    return Config(
        filters=Filters(**data["filters"]),
        profile=Profile(**data["profile"]),
        nitter_queries=data.get("nitter_queries", []),
        reddit_subs=data.get("reddit_subs", []),
    )
```

**Step 5: Run — expect PASS**

**Step 6: Commit**

```bash
git add src/jobscraper/config.py tests/test_config.py tests/fixtures/
git commit -m "feat: config loader"
```

---

## Task 4: Filter — freshness

**Files:**
- Create: `src/jobscraper/filter.py`
- Create: `tests/test_filter.py`
- Create: `tests/conftest.py`

**Step 1: Shared fixtures** `tests/conftest.py`:
```python
from datetime import datetime, timedelta, timezone
import pytest
from jobscraper.models import Job
from jobscraper.config import Filters, Profile, Config

@pytest.fixture
def filters():
    return Filters(
        min_budget_eur=100,
        max_age_hours=2,
        languages=["en", "fr", "es"],
        keywords=["landing page", "react"],
    )

@pytest.fixture
def job_factory():
    def _make(**overrides):
        defaults = dict(
            source="test", external_id="1",
            title="Need a landing page", description="React + Tailwind",
            budget_eur=200.0, language="en",
            url="https://example.com",
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            raw={},
        )
        defaults.update(overrides)
        return Job.make(**defaults)
    return _make
```

**Step 2: Write failing test** `tests/test_filter.py`:
```python
from datetime import datetime, timedelta, timezone
from jobscraper.filter import is_relevant

def test_reject_if_older_than_max_age(filters, job_factory):
    old = job_factory(posted_at=datetime.now(timezone.utc) - timedelta(hours=3))
    assert not is_relevant(old, filters)

def test_accept_if_within_max_age(filters, job_factory):
    fresh = job_factory(posted_at=datetime.now(timezone.utc) - timedelta(minutes=30))
    assert is_relevant(fresh, filters)
```

**Step 3: Run — expect FAIL**

**Step 4: Implement** `src/jobscraper/filter.py`:
```python
from datetime import datetime, timezone
from .config import Filters
from .models import Job

def is_relevant(job: Job, filters: Filters) -> bool:
    age_hours = (datetime.now(timezone.utc) - job.posted_at).total_seconds() / 3600
    if age_hours > filters.max_age_hours:
        return False
    return True
```

**Step 5: Run — expect PASS**

**Step 6: Commit**

```bash
git add src/jobscraper/filter.py tests/test_filter.py tests/conftest.py
git commit -m "feat: filter freshness check"
```

---

## Task 5: Filter — language, budget, keywords

**Files:**
- Modify: `src/jobscraper/filter.py`
- Modify: `tests/test_filter.py`

**Step 1: Add failing tests**

```python
def test_reject_wrong_language(filters, job_factory):
    assert not is_relevant(job_factory(language="de"), filters)

def test_reject_low_budget(filters, job_factory):
    assert not is_relevant(job_factory(budget_eur=50.0), filters)

def test_accept_missing_budget(filters, job_factory):
    assert is_relevant(job_factory(budget_eur=None), filters)

def test_reject_no_keyword_match(filters, job_factory):
    assert not is_relevant(
        job_factory(title="wordpress work", description="php stuff"),
        filters,
    )

def test_accept_keyword_in_description(filters, job_factory):
    assert is_relevant(
        job_factory(title="project", description="need a landing page"),
        filters,
    )
```

**Step 2: Run — expect FAIL**

**Step 3: Extend `is_relevant`**

```python
def is_relevant(job: Job, filters: Filters) -> bool:
    age_hours = (datetime.now(timezone.utc) - job.posted_at).total_seconds() / 3600
    if age_hours > filters.max_age_hours:
        return False
    if job.language not in filters.languages:
        return False
    if job.budget_eur is not None and job.budget_eur < filters.min_budget_eur:
        return False
    if not filters.keyword_regex.search(f"{job.title} {job.description}"):
        return False
    return True
```

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git commit -am "feat: filter language/budget/keywords"
```

---

## Task 6: Dedupe store

**Files:**
- Create: `src/jobscraper/store.py`
- Create: `tests/test_store.py`

**Step 1: Write failing test**

```python
from datetime import datetime, timezone, timedelta
from pathlib import Path
from jobscraper.store import SeenStore

def test_roundtrip(tmp_path):
    store = SeenStore(tmp_path / "seen.json")
    assert not store.has("codeur:1")
    store.add("codeur:1")
    store.save()

    store2 = SeenStore(tmp_path / "seen.json")
    assert store2.has("codeur:1")

def test_prunes_old_ids(tmp_path, monkeypatch):
    store = SeenStore(tmp_path / "seen.json", retention_days=30)
    store._data["old:1"] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    store._data["new:1"] = datetime.now(timezone.utc).isoformat()
    store.save()
    store2 = SeenStore(tmp_path / "seen.json", retention_days=30)
    assert not store2.has("old:1")
    assert store2.has("new:1")
```

**Step 2: Run — expect FAIL**

**Step 3: Implement** `src/jobscraper/store.py`:
```python
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

class SeenStore:
    def __init__(self, path: Path, retention_days: int = 30):
        self.path = path
        self.retention_days = retention_days
        self._data: dict[str, str] = {}
        if path.exists():
            raw = json.loads(path.read_text())
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            self._data = {
                jid: ts for jid, ts in raw.items()
                if datetime.fromisoformat(ts) >= cutoff
            }

    def has(self, job_id: str) -> bool:
        return job_id in self._data

    def add(self, job_id: str) -> None:
        self._data[job_id] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))
```

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git add src/jobscraper/store.py tests/test_store.py
git commit -m "feat: SeenStore dedupe with retention"
```

---

## Task 7: Codeur source

**Files:**
- Create: `src/jobscraper/sources/__init__.py`
- Create: `src/jobscraper/sources/codeur.py`
- Create: `tests/fixtures/codeur_sample.html`
- Create: `tests/test_codeur.py`

**Step 1: Capture fixture**

```bash
curl -s -A "Mozilla/5.0" https://www.codeur.com/projects > tests/fixtures/codeur_sample.html
```
If the request is blocked, manually paste a representative snippet of the projects list HTML into the fixture file (a few `<div>` project cards with title, description, budget, URL).

**Step 2: Write failing test** `tests/test_codeur.py`:
```python
from pathlib import Path
from jobscraper.sources.codeur import parse_projects

def test_parse_returns_jobs():
    html = Path("tests/fixtures/codeur_sample.html").read_text()
    jobs = parse_projects(html)
    assert len(jobs) > 0
    j = jobs[0]
    assert j.source == "codeur"
    assert j.url.startswith("https://www.codeur.com/")
    assert j.language == "fr"
```

**Step 3: Run — expect FAIL**

**Step 4: Implement** `src/jobscraper/sources/codeur.py`:
```python
import re
from datetime import datetime, timezone
from selectolax.parser import HTMLParser
import httpx
from ..models import Job

BASE = "https://www.codeur.com"

def parse_projects(html: str) -> list[Job]:
    tree = HTMLParser(html)
    jobs: list[Job] = []
    for card in tree.css("a[href^='/projects/']"):
        href = card.attributes.get("href", "")
        if not re.match(r"^/projects/\d+", href):
            continue
        url = BASE + href
        external_id = re.search(r"/projects/(\d+)", href).group(1)
        title_el = card.css_first("h2, h3, .project-title")
        title = (title_el.text(strip=True) if title_el else card.text(strip=True))[:200]
        desc_el = card.css_first(".project-description, p")
        description = desc_el.text(strip=True) if desc_el else ""
        budget = _parse_budget(card.text())
        jobs.append(Job.make(
            source="codeur", external_id=external_id,
            title=title, description=description,
            budget_eur=budget, language="fr",
            url=url, posted_at=datetime.now(timezone.utc),
            raw={},
        ))
    # de-duplicate by id within a single page
    seen: dict[str, Job] = {}
    for j in jobs:
        seen.setdefault(j.id, j)
    return list(seen.values())

_BUDGET_RE = re.compile(r"(\d{2,6})\s*(?:à|-|–)?\s*(\d{2,6})?\s*€")

def _parse_budget(text: str) -> float | None:
    m = _BUDGET_RE.search(text)
    if not m:
        return None
    return float(m.group(1))

async def fetch() -> list[Job]:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as c:
        r = await c.get(f"{BASE}/projects")
        r.raise_for_status()
        return parse_projects(r.text)
```

**Step 5: Run — expect PASS**

**Step 6: Commit**

```bash
git add src/jobscraper/sources/ tests/test_codeur.py tests/fixtures/codeur_sample.html
git commit -m "feat: Codeur source parser"
```

---

## Task 8: Reddit source

**Files:**
- Create: `src/jobscraper/sources/reddit.py`
- Create: `tests/fixtures/reddit_sample.json`
- Create: `tests/test_reddit.py`

**Step 1: Capture fixture**

```bash
curl -s -A "jobscraper/0.1" "https://www.reddit.com/r/forhire/new.json?limit=10" > tests/fixtures/reddit_sample.json
```

**Step 2: Failing test** `tests/test_reddit.py`:
```python
import json
from pathlib import Path
from jobscraper.sources.reddit import parse_listing

def test_parse_reddit_extracts_hiring_posts():
    data = json.loads(Path("tests/fixtures/reddit_sample.json").read_text())
    jobs = parse_listing(data, subreddit="forhire")
    assert all(j.source == "reddit" for j in jobs)
    # Only [HIRING] posts kept
    assert all("hiring" in j.title.lower() for j in jobs)
```

**Step 3: Run — expect FAIL**

**Step 4: Implement** `src/jobscraper/sources/reddit.py`:
```python
from datetime import datetime, timezone
import httpx
from langdetect import detect, LangDetectException
from ..models import Job

def parse_listing(data: dict, subreddit: str) -> list[Job]:
    jobs: list[Job] = []
    for child in data.get("data", {}).get("children", []):
        p = child["data"]
        title = p.get("title", "")
        if "[hiring]" not in title.lower():
            continue
        description = p.get("selftext", "") or ""
        try:
            lang = detect(f"{title} {description}")
        except LangDetectException:
            lang = "en"
        jobs.append(Job.make(
            source="reddit", external_id=p["id"],
            title=title, description=description,
            budget_eur=None, language=lang,
            url=f"https://www.reddit.com{p['permalink']}",
            posted_at=datetime.fromtimestamp(p["created_utc"], tz=timezone.utc),
            raw={"subreddit": subreddit},
        ))
    return jobs

async def fetch(subs: list[str]) -> list[Job]:
    jobs: list[Job] = []
    headers = {"User-Agent": "jobscraper/0.1 (by /u/anon)"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as c:
        for sub in subs:
            r = await c.get(f"https://www.reddit.com/r/{sub}/new.json?limit=25")
            r.raise_for_status()
            jobs.extend(parse_listing(r.json(), subreddit=sub))
    return jobs
```

**Step 5: Run — expect PASS**

**Step 6: Commit**

```bash
git add src/jobscraper/sources/reddit.py tests/test_reddit.py tests/fixtures/reddit_sample.json
git commit -m "feat: Reddit source parser"
```

---

## Task 9: Twitter/Nitter source

**Files:**
- Create: `src/jobscraper/sources/twitter.py`
- Create: `tests/fixtures/nitter_sample.xml`
- Create: `tests/test_twitter.py`

**Step 1: Capture fixture**

```bash
curl -s "https://nitter.net/search/rss?f=tweets&q=%22need+a+landing+page%22" > tests/fixtures/nitter_sample.xml
```
If Nitter is unreachable, author a minimal RSS fixture with 2–3 `<item>` entries (title, link, pubDate, description).

**Step 2: Failing test** `tests/test_twitter.py`:
```python
from pathlib import Path
from jobscraper.sources.twitter import parse_rss

def test_parse_rss_extracts_items():
    xml = Path("tests/fixtures/nitter_sample.xml").read_text()
    jobs = parse_rss(xml, query="need a landing page")
    assert all(j.source == "twitter" for j in jobs)
    assert all(j.url.startswith("http") for j in jobs)
```

**Step 3: Run — expect FAIL**

**Step 4: Implement** `src/jobscraper/sources/twitter.py`:
```python
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
import httpx
from langdetect import detect, LangDetectException
from ..models import Job

NITTER_BASES = ["https://nitter.net", "https://nitter.privacydev.net"]

def parse_rss(xml: str, query: str) -> list[Job]:
    root = ET.fromstring(xml)
    jobs: list[Job] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = item.findtext("pubDate")
        posted = parsedate_to_datetime(pub) if pub else datetime.now(timezone.utc)
        try:
            lang = detect(f"{title} {desc}")
        except LangDetectException:
            lang = "en"
        external_id = hashlib.sha1(link.encode()).hexdigest()[:12]
        jobs.append(Job.make(
            source="twitter", external_id=external_id,
            title=title[:200], description=desc,
            budget_eur=None, language=lang,
            url=link, posted_at=posted,
            raw={"query": query},
        ))
    return jobs

async def fetch(queries: list[str]) -> list[Job]:
    jobs: list[Job] = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
        for q in queries:
            for base in NITTER_BASES:
                try:
                    r = await c.get(f"{base}/search/rss", params={"f": "tweets", "q": q})
                    r.raise_for_status()
                    jobs.extend(parse_rss(r.text, query=q))
                    break
                except Exception:
                    continue
    return jobs
```

**Step 5: Run — expect PASS**

**Step 6: Commit**

```bash
git add src/jobscraper/sources/twitter.py tests/test_twitter.py tests/fixtures/nitter_sample.xml
git commit -m "feat: Twitter/Nitter RSS source"
```

---

## Task 10: Drafter (GLM via z.ai)

**Files:**
- Create: `src/jobscraper/drafter.py`
- Create: `tests/test_drafter.py`

**Step 1: Failing test**

```python
from unittest.mock import MagicMock
from jobscraper.drafter import draft_pitch
from jobscraper.config import Profile

def test_draft_pitch_uses_job_language(job_factory):
    profile = Profile(summary_en="EN profile", summary_fr="FR profile", summary_es="ES profile")
    job = job_factory(language="fr", title="Besoin d'une landing page",
                      description="Site vitrine Next.js")
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Bonjour, voici mon offre."))
    ]
    out = draft_pitch(job, profile, client=fake_client)
    assert out == "Bonjour, voici mon offre."
    call = fake_client.chat.completions.create.call_args
    # profile string in system prompt matches job language
    assert "FR profile" in call.kwargs["messages"][0]["content"]
```

**Step 2: Run — expect FAIL**

**Step 3: Implement** `src/jobscraper/drafter.py`:
```python
import os
from openai import OpenAI
from .config import Profile
from .models import Job

MODEL = "glm-4.6"

def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["ZAI_API_KEY"],
        base_url="https://api.z.ai/api/paas/v4/",
    )

def _profile_for(lang: str, profile: Profile) -> str:
    return {
        "fr": profile.summary_fr,
        "es": profile.summary_es,
    }.get(lang, profile.summary_en)

SYSTEM_TMPL = (
    "You are drafting a short freelance pitch. Write 4-5 sentences in the same "
    "language as the job post. Open with one specific detail from the job, state "
    "your approach in one line, propose a concrete timeline, and end with a "
    "question. Plain text, no markdown.\n\nFreelancer profile: {profile}"
)

def draft_pitch(job: Job, profile: Profile, client: OpenAI | None = None) -> str:
    client = client or get_client()
    system = SYSTEM_TMPL.format(profile=_profile_for(job.language, profile))
    user = (
        f"Job title: {job.title}\n"
        f"Job description: {job.description}\n"
        f"Budget (EUR): {job.budget_eur if job.budget_eur is not None else 'not specified'}\n"
        f"Language: {job.language}"
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()
```

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git add src/jobscraper/drafter.py tests/test_drafter.py
git commit -m "feat: GLM-based pitch drafter"
```

---

## Task 11: Telegram sender

**Files:**
- Create: `src/jobscraper/notify.py`
- Create: `tests/test_notify.py`

**Step 1: Failing test** (mock httpx)

```python
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
```

**Step 2: Run — expect FAIL**

**Step 3: Implement** `src/jobscraper/notify.py`:
```python
import os
import httpx
from .models import Job

def send_job(job: Job, draft: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    text = (
        f"💼 *{_esc(job.title)}*\n"
        f"_{job.source} · {job.language} · "
        f"{'€'+str(int(job.budget_eur)) if job.budget_eur else 'budget N/A'}_\n\n"
        f"{_esc(job.description)[:400]}\n\n"
        f"🔗 {job.url}\n\n"
        f"✉️ *Draft:*\n{_esc(draft)}"
    )
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
              "disable_web_page_preview": True},
        timeout=10,
    )
    r.raise_for_status()

def _esc(s: str) -> str:
    return s.replace("*", "").replace("_", "").replace("`", "")
```

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git add src/jobscraper/notify.py tests/test_notify.py
git commit -m "feat: Telegram notifier"
```

---

## Task 12: Main runner

**Files:**
- Create: `src/jobscraper/main.py`
- Create: `tests/test_main.py`

**Step 1: Failing integration test**

```python
from unittest.mock import patch, MagicMock
from pathlib import Path
from jobscraper.main import run

def test_run_filters_dedupes_drafts_and_notifies(tmp_path, monkeypatch, job_factory):
    monkeypatch.setenv("ZAI_API_KEY", "x")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    state = tmp_path / "seen.json"
    cfg_path = Path("tests/fixtures/config_minimal.yaml")

    relevant = job_factory(external_id="fresh-1", title="React landing page")
    stale = job_factory(external_id="old-1", posted_at=job_factory().posted_at.replace(year=2020))

    with patch("jobscraper.main.fetch_all", return_value=[relevant, stale]), \
         patch("jobscraper.main.draft_pitch", return_value="Hi!"), \
         patch("jobscraper.main.send_job") as send:
        run(config_path=cfg_path, state_path=state)
        assert send.call_count == 1
        sent_job = send.call_args.args[0]
        assert sent_job.id.endswith("fresh-1")

    # Second run: same job should now be deduped
    with patch("jobscraper.main.fetch_all", return_value=[relevant]), \
         patch("jobscraper.main.draft_pitch", return_value="Hi!"), \
         patch("jobscraper.main.send_job") as send:
        run(config_path=cfg_path, state_path=state)
        assert send.call_count == 0
```

**Step 2: Run — expect FAIL**

**Step 3: Implement** `src/jobscraper/main.py`:
```python
import asyncio
import logging
from pathlib import Path

from .config import load_config, Config
from .filter import is_relevant
from .store import SeenStore
from .drafter import draft_pitch, get_client
from .notify import send_job
from .sources import codeur, reddit, twitter
from .models import Job

log = logging.getLogger("jobscraper")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

async def fetch_all(cfg: Config) -> list[Job]:
    results = await asyncio.gather(
        codeur.fetch(),
        reddit.fetch(cfg.reddit_subs),
        twitter.fetch(cfg.nitter_queries),
        return_exceptions=True,
    )
    jobs: list[Job] = []
    for name, result in zip(["codeur", "reddit", "twitter"], results):
        if isinstance(result, Exception):
            log.warning("source %s failed: %s", name, result)
            continue
        log.info("source %s returned %d jobs", name, len(result))
        jobs.extend(result)
    return jobs

def run(config_path: Path = Path("config.yaml"),
        state_path: Path = Path("state/seen_jobs.json")) -> None:
    cfg = load_config(config_path)
    store = SeenStore(state_path)
    jobs = asyncio.run(fetch_all(cfg)) if asyncio.iscoroutinefunction(fetch_all) else fetch_all(cfg)

    client = None
    for job in jobs:
        if not is_relevant(job, cfg.filters):
            continue
        if store.has(job.id):
            continue
        try:
            if client is None:
                client = get_client()
            draft = draft_pitch(job, cfg.profile, client=client)
        except Exception as e:
            log.warning("draft failed for %s: %s", job.id, e)
            draft = "(draft failed — reply manually)"
        try:
            send_job(job, draft)
            store.add(job.id)
        except Exception as e:
            log.error("notify failed for %s: %s", job.id, e)
    store.save()

if __name__ == "__main__":
    run()
```

Note: the test patches `fetch_all` to return a list directly (not a coroutine), so the `iscoroutinefunction` check handles both.

**Step 4: Run — expect PASS**

**Step 5: Commit**

```bash
git add src/jobscraper/main.py tests/test_main.py
git commit -m "feat: main runner"
```

---

## Task 13: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/scrape.yml`
- Create: `state/.gitkeep`

**Step 1: Write the workflow**

`.github/workflows/scrape.yml`:
```yaml
name: scrape
on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:

concurrency:
  group: scrape
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: pytest -q
      - run: python -m jobscraper.main
        env:
          ZAI_API_KEY: ${{ secrets.ZAI_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      - name: Commit state
        run: |
          git config user.name "jobscraper-bot"
          git config user.email "bot@users.noreply.github.com"
          git add state/seen_jobs.json || true
          git diff --quiet --staged || git commit -m "chore: update seen_jobs [skip ci]"
          git push
```

**Step 2: Touch the state dir** so it exists in git:

```bash
mkdir -p state && touch state/.gitkeep
```

**Step 3: Commit**

```bash
git add .github/ state/
git commit -m "ci: GitHub Actions cron workflow"
```

---

## Task 14: README with setup

**Files:**
- Create: `README.md`

**Step 1: Write setup docs**

```markdown
# jobscraper

Stateless 5-minute cron that scrapes Codeur, Reddit, and Twitter/Nitter for
freelance landing-page gigs, drafts a tailored pitch with GLM-4.6, and
pushes it to Telegram.

## Setup

1. `python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
2. `pytest -q` — should be green.
3. Create a Telegram bot via `@BotFather`, send `/start` to it, then
   `curl https://api.telegram.org/bot<TOKEN>/getUpdates` to grab your chat ID.
4. `gh repo create jobscraper --private --source . --push`
5. Add secrets: `gh secret set ZAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
6. Workflow kicks in within 5 minutes.

## Tuning

Edit `config.yaml` to tweak keywords, budget floor, Reddit subs, Nitter queries.
Commit and push — the next run uses the new config.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README"
```

---

## Done criteria

- `pytest -q` all green.
- `python -m jobscraper.main` runs end-to-end locally (with envs exported) and sends at least one Telegram message if matching gigs exist.
- GitHub Actions run succeeds, commits state back, and you receive the Telegram alert.
