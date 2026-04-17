from pathlib import Path
from jobscraper.sources.codeur import parse_projects, _parse_budget, _parse_time_ago


def test_parse_returns_jobs():
    html = Path("tests/fixtures/codeur_sample.html").read_text()
    jobs = parse_projects(html)
    assert len(jobs) > 0
    j = jobs[0]
    assert j.source == "codeur"
    assert j.url.startswith("https://www.codeur.com/projects/")
    assert j.language == "fr"
    assert j.title  # non-empty


def test_parse_budget_range():
    assert _parse_budget("200 à 500 €") == 200.0
    assert _parse_budget("500 €") == 500.0
    assert _parse_budget("Moins de 500 €") == 0.0
    assert _parse_budget("pas défini") is None


def test_parse_time_ago_minutes():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    got = _parse_time_ago("Il y a 30 minutes", now=now)
    assert (now - got) < timedelta(minutes=31)
    assert (now - got) > timedelta(minutes=29)


def test_parse_time_ago_hours():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    got = _parse_time_ago("Il y a 2 heures", now=now)
    assert timedelta(hours=1, minutes=59) < (now - got) < timedelta(hours=2, minutes=1)
