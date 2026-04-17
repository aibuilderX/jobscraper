from datetime import datetime, timezone
from .config import Filters
from .models import Job


def is_relevant(job: Job, filters: Filters) -> bool:
    age_hours = (datetime.now(timezone.utc) - job.posted_at).total_seconds() / 3600
    if age_hours > filters.max_age_hours:
        return False
    if job.language not in filters.languages:
        return False
    if job.budget_eur is not None and job.budget_eur < filters.min_budget_eur:
        return False
    if not filters.keyword_regex.search(f"{job.title} {job.description}"):
        return False
    return True
