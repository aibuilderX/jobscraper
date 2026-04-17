from datetime import datetime, timezone
import dataclasses
from jobscraper.models import Job


def test_job_id_is_stable_hash():
    j = Job.make(
        source="codeur", external_id="abc123",
        title="t", description="d",
        budget_eur=100.0, language="fr",
        url="https://example.com",
        posted_at=datetime.now(timezone.utc),
        raw={},
    )
    assert j.id == "codeur:abc123"


def test_job_is_frozen():
    j = Job.make(
        source="codeur", external_id="x",
        title="t", description="d",
        budget_eur=None, language="en",
        url="https://example.com",
        posted_at=datetime.now(timezone.utc),
        raw={},
    )
    assert dataclasses.is_dataclass(j)
