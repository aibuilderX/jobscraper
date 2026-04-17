# Jobscraper — Design

**Date:** 2026-04-17
**Goal:** Land actual freelance gigs (landing pages, small dev work) as a bilingual FR/EN/ES vibe coder by being the first to reply with a tailored pitch.

## Sources (high-signal only)

- **Codeur.com** — public French project listings, scraped via HTML.
- **Reddit** — `/r/forhire`, `/r/slavelabour`, `/r/hiring` via public `.json` endpoints.
- **Twitter/X** — Nitter RSS search for landing-page/dev-need posts in EN/FR/ES.

Deliberately excluded: Upwork, Fiverr (saturated, review-gated, scraping risk), Toloka/Clickworker (data labeling, not dev).

## Runtime

- **GitHub Actions cron** `*/5 * * * *`, stateless, free.
- State persisted by committing `state/seen_jobs.json` back to the repo.

## Pipeline

1. Parallel fetch from 3 sources (`asyncio.gather`, 10s timeout each, one-source failure is non-fatal).
2. Normalize to `Job` records.
3. Filter: freshness <2h → language in {en, fr, es} → budget ≥ €100 (None passes) → keyword regex match.
4. Dedupe against `seen_jobs.json` (30-day window).
5. For each new relevant job: draft a pitch via GLM-4.6 (z.ai OpenAI-compatible API).
6. Send Telegram message (job summary + link + draft).
7. Commit updated `seen_jobs.json`.

## Job schema

```python
@dataclass
class Job:
    id: str              # "{source}:{hash}"
    source: str
    title: str
    description: str
    budget_eur: float | None
    language: str        # "en" | "fr" | "es"
    url: str
    posted_at: datetime
    raw: dict
```

## Keyword regex (editable in `config.yaml`)

```
landing page | one.?pager | site vitrine | page d.atterrissage |
página de aterrizaje | site web simple | sitio web simple |
next.?js | react | tailwind | framer | webflow | astro |
website | site web | sitio web
```

## Draft prompt

System: bilingual FR/EN/ES dev, fast Next.js + Tailwind landing pages, 48h delivery.
User: job title + description + budget.
Output: 4–5 sentences, opens with a specific job detail, states approach, proposes timeline, ends with a question. Same language as job post. Plain text.

Model: `glm-4.6` via `https://api.z.ai/api/paas/v4/` using `openai` SDK. Fallback `glm-4.5-air`.

## Secrets (GitHub repo)

- `ZAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Tech stack

Python 3.12, `httpx`, `selectolax`, `openai`, `python-telegram-bot`, `langdetect`, `pytest`.

## Error handling

- Per-source failures logged, other sources still run.
- Per-job LLM/Telegram failures wrapped; fallback is a raw alert without draft so no gig is silently dropped.

## Testing

- Filter unit tests with fixtures.
- Parser tests with saved HTML fixtures (detect site layout changes early).
- Integration test with mocked HTTP, z.ai, Telegram clients.
- CI runs tests before each cron execution.

## First-week loop

Review alerts weekly, tune `config.yaml` (keywords, budget floor). Expect 2–3 iterations.
