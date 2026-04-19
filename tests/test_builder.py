import json
from datetime import datetime, timezone
from pathlib import Path
from jobscraper.builder import is_website_job, queue_build, build_command
from jobscraper.models import Job


def _job(title="Need a landing page", desc="Simple site vitrine", lang="en") -> Job:
    return Job.make(
        source="codeur",
        external_id="123",
        title=title,
        description=desc,
        budget_eur=500,
        language=lang,
        url="https://codeur.com/projects/123",
        posted_at=datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
    )


def test_is_website_job_matches_landing():
    assert is_website_job(_job(title="Create a landing page"))


def test_is_website_job_matches_fr():
    assert is_website_job(_job(title="Besoin d'un site vitrine", lang="fr"))


def test_is_website_job_rejects_unrelated():
    j = _job(title="Need a python data scraper", desc="ETL pipeline")
    assert not is_website_job(j)


def test_queue_build_writes_json(tmp_path: Path):
    j = _job()
    path = queue_build(j, out_dir=tmp_path)
    data = json.loads(path.read_text())
    assert data["id"] == j.id
    assert data["title"] == j.title
    assert data["posted_at"].startswith("2026-04-18")


def test_build_command_contains_safe_id():
    j = _job()
    cmd = build_command(j)
    # colon in id should be sanitized
    assert ":" not in cmd.split("job_id=")[1]
    assert "codeur" in cmd
