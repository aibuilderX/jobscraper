from datetime import datetime, timedelta, timezone
import pytest
from jobscraper.models import Job
from jobscraper.config import Filters


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
            source="test",
            external_id="1",
            title="Need a landing page",
            description="React + Tailwind",
            budget_eur=200.0,
            language="en",
            url="https://example.com",
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            raw={},
        )
        defaults.update(overrides)
        return Job.make(**defaults)

    return _make
