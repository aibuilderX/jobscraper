from datetime import datetime, timedelta, timezone
from jobscraper.filter import is_relevant


def test_reject_if_older_than_max_age(filters, job_factory):
    old = job_factory(posted_at=datetime.now(timezone.utc) - timedelta(hours=3))
    assert not is_relevant(old, filters)


def test_accept_if_within_max_age(filters, job_factory):
    fresh = job_factory(posted_at=datetime.now(timezone.utc) - timedelta(minutes=30))
    assert is_relevant(fresh, filters)


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
