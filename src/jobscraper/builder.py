import json
import re
from dataclasses import asdict
from pathlib import Path
from .models import Job

_WEBSITE_PAT = re.compile(
    r"landing\s*page|one.?pager|site\s*vitrine|site\s*web|página\s*de\s*aterrizaje|sitio\s*web|website",
    re.IGNORECASE,
)

PENDING_DIR = Path("state/pending_builds")


def is_website_job(job: Job) -> bool:
    return bool(_WEBSITE_PAT.search(f"{job.title} {job.description}"))


def _safe_name(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", job_id)


def queue_build(job: Job, out_dir: Path = PENDING_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_safe_name(job.id)}.json"
    payload = asdict(job)
    # datetime -> iso
    payload["posted_at"] = job.posted_at.isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def build_command(job: Job, repo: str = "aibuilderX/jobscraper") -> str:
    return f"gh workflow run builder.yml -R {repo} -f job_id={_safe_name(job.id)}"
