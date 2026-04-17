from datetime import datetime, timezone, timedelta
from jobscraper.store import SeenStore


def test_roundtrip(tmp_path):
    store = SeenStore(tmp_path / "seen.json")
    assert not store.has("codeur:1")
    store.add("codeur:1")
    store.save()

    store2 = SeenStore(tmp_path / "seen.json")
    assert store2.has("codeur:1")


def test_prunes_old_ids(tmp_path):
    store = SeenStore(tmp_path / "seen.json", retention_days=30)
    store._data["old:1"] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    store._data["new:1"] = datetime.now(timezone.utc).isoformat()
    store.save()
    store2 = SeenStore(tmp_path / "seen.json", retention_days=30)
    assert not store2.has("old:1")
    assert store2.has("new:1")
