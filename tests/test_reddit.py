import json
from pathlib import Path
from jobscraper.sources.reddit import parse_listing


def test_parse_reddit_extracts_hiring_posts():
    data = json.loads(Path("tests/fixtures/reddit_sample.json").read_text())
    jobs = parse_listing(data, subreddit="forhire")
    assert len(jobs) > 0
    assert all(j.source == "reddit" for j in jobs)
    assert all("hiring" in j.title.lower() for j in jobs)


def test_parse_reddit_extracts_url_and_time():
    data = json.loads(Path("tests/fixtures/reddit_sample.json").read_text())
    jobs = parse_listing(data, subreddit="forhire")
    j = jobs[0]
    assert j.url.startswith("https://www.reddit.com/")
    assert j.posted_at is not None
