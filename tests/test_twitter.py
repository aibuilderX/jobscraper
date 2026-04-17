from pathlib import Path
from jobscraper.sources.twitter import parse_rss


def test_parse_rss_extracts_items():
    xml = Path("tests/fixtures/nitter_sample.xml").read_text()
    jobs = parse_rss(xml, query="landing page")
    assert len(jobs) == 3
    assert all(j.source == "twitter" for j in jobs)
    assert all(j.url.startswith("http") for j in jobs)


def test_parse_rss_detects_fr():
    xml = Path("tests/fixtures/nitter_sample.xml").read_text()
    jobs = parse_rss(xml, query="landing page")
    fr = [j for j in jobs if j.language == "fr"]
    assert len(fr) == 1
    assert "Cherche" in fr[0].title
