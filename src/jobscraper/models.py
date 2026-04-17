from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Job:
    id: str
    source: str
    title: str
    description: str
    budget_eur: float | None
    language: str
    url: str
    posted_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def make(cls, *, source: str, external_id: str, **kwargs) -> "Job":
        return cls(id=f"{source}:{external_id}", source=source, **kwargs)
