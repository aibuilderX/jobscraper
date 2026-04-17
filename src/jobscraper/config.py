import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass(frozen=True)
class Filters:
    min_budget_eur: float
    max_age_hours: float
    languages: list[str]
    keywords: list[str]
    keyword_regex: re.Pattern = field(init=False, compare=False, repr=False)

    def __post_init__(self):
        joined = "|".join(self.keywords)
        object.__setattr__(self, "keyword_regex", re.compile(joined, re.IGNORECASE))


@dataclass(frozen=True)
class Profile:
    summary_en: str
    summary_fr: str
    summary_es: str


@dataclass(frozen=True)
class Config:
    filters: Filters
    profile: Profile
    nitter_queries: list[str]
    reddit_subs: list[str]


def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text())
    return Config(
        filters=Filters(**data["filters"]),
        profile=Profile(**data["profile"]),
        nitter_queries=data.get("nitter_queries", []),
        reddit_subs=data.get("reddit_subs", []),
    )
