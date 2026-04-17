import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


class SeenStore:
    def __init__(self, path: Path, retention_days: int = 30):
        self.path = Path(path)
        self.retention_days = retention_days
        self._data: dict[str, str] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            self._data = {
                jid: ts
                for jid, ts in raw.items()
                if datetime.fromisoformat(ts) >= cutoff
            }

    def has(self, job_id: str) -> bool:
        return job_id in self._data

    def add(self, job_id: str) -> None:
        self._data[job_id] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))
