import json
from pathlib import Path
from jobscraper.sources.remoteok import parse_listing


def test_parse_skips_legal_entry():
    data = json.loads(Path("tests/fixtures/remoteok_sample.json").read_text())
    jobs = parse_listing(data)
    # fixture has 1 legal + 4 jobs
    assert len(jobs) == 4
    assert all(j.source == "remoteok" for j in jobs)


def test_parse_extracts_fields():
    data = json.loads(Path("tests/fixtures/remoteok_sample.json").read_text())
    jobs = parse_listing(data)
    j = jobs[0]
    assert j.url.startswith("https://")
    assert j.language == "en"
    # salary 0 should yield None budget
    assert j.budget_eur is None or j.budget_eur > 0
    # HTML tags stripped from description
    assert "<p>" not in j.description


def test_parse_converts_usd_to_eur():
    # Craft a synthetic entry with a salary so we can verify conversion
    synthetic = [
        {"legal": "notice"},
        {
            "id": "999",
            "position": "Next.js Landing Page Developer",
            "company": "Acme",
            "tags": ["react", "next.js"],
            "description": "<p>Build a landing page.</p>",
            "url": "https://remoteok.com/remote-jobs/acme-999",
            "date": "2026-04-17T12:00:00+00:00",
            "salary_min": 1200,
            "salary_max": 2000,
            "location": "Remote",
        },
    ]
    jobs = parse_listing(synthetic)
    assert len(jobs) == 1
    # USD 1200 ≈ EUR ~1100 (rate ~0.92)
    assert 1000 < jobs[0].budget_eur < 1200
