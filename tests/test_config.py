from pathlib import Path
from jobscraper.config import load_config


def test_load_config_parses_fields():
    cfg = load_config(Path("tests/fixtures/config_minimal.yaml"))
    assert cfg.filters.min_budget_eur == 50
    assert cfg.filters.max_age_hours == 1
    assert cfg.filters.languages == ["en"]
    assert "react" in cfg.filters.keywords
    assert cfg.profile.summary_en == "test profile"


def test_keyword_regex_matches_case_insensitively():
    cfg = load_config(Path("tests/fixtures/config_minimal.yaml"))
    assert cfg.filters.keyword_regex.search("Need a LANDING PAGE quick")
