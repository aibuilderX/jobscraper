# jobscraper

Stateless 5-minute cron that scrapes **Codeur.com**, **Reddit**, and **Twitter/Nitter** for
freelance landing-page gigs, drafts a tailored pitch with **GLM-4.6** (via z.ai),
and pushes it to **Telegram**.

Targets bilingual FR/EN/ES freelancers. Filters on freshness (<2h), language,
budget floor (€100), and a keyword regex. State is persisted in
`state/seen_jobs.json`, committed back by the workflow.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q          # should be green
```

### 1. Create a Telegram bot

- Message `@BotFather` on Telegram, send `/newbot`, follow prompts.
- Copy the bot **token**.
- Send `/start` to your new bot.
- Fetch your chat ID:
  ```bash
  curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
  ```
  Look for `"chat":{"id": <CHAT_ID>,...}`.

### 2. Get a z.ai API key

Sign up at [z.ai](https://z.ai/) and create an API key for GLM-4.6.

### 3. Push to GitHub and add secrets

```bash
gh repo create jobscraper --private --source . --push
gh secret set ZAI_API_KEY
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
```

The workflow runs every 5 minutes from then on. Trigger a first run manually
via the Actions tab → "scrape" → "Run workflow", or:

```bash
gh workflow run scrape.yml
```

## Local smoke test

```bash
export ZAI_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
.venv/bin/python -m jobscraper.main
```

## Tuning

Everything is in [config.yaml](config.yaml):

- `filters.keywords` — regex list of phrases that must appear in title or description.
- `filters.min_budget_eur` — budget floor (jobs with no budget pass).
- `filters.max_age_hours` — reject anything older than this.
- `filters.languages` — accepted post languages.
- `reddit_subs` — subreddits to poll.
- `nitter_queries` — Twitter search queries via Nitter RSS.
- `profile` — your pitch blurb (EN / FR / ES).

Commit changes; the next cron run uses the updated config.

## Known limitations

- **Nitter availability:** public Nitter instances are often rate-limited or
  down. If all instances fail, the Twitter source silently returns nothing
  (the run continues). Swap in a paid X API later if this becomes a problem.
- **Codeur HTML drift:** the parser relies on the current project-card DOM.
  If Codeur redesigns, [tests/test_codeur.py](tests/test_codeur.py) will fail
  first — update the fixture and selectors together.
- **Reddit auth:** unauthenticated `.json` endpoints are rate-limited.
  Usually fine at 5-minute cadence, but if you hit 429s, add a Reddit app
  and use OAuth.
