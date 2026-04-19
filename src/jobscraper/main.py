import asyncio
import logging
from pathlib import Path

from .config import load_config, Config
from .filter import is_relevant
from .store import SeenStore
from .drafter import draft_pitch, get_client
from .notify import send_job
from .builder import is_website_job, queue_build, build_command
from .sources import codeur, remoteok, twitter
from .models import Job

log = logging.getLogger("jobscraper")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def fetch_all(cfg: Config) -> list[Job]:
    results = await asyncio.gather(
        codeur.fetch(),
        remoteok.fetch(),
        twitter.fetch(cfg.nitter_queries),
        return_exceptions=True,
    )
    jobs: list[Job] = []
    for name, result in zip(["codeur", "remoteok", "twitter"], results):
        if isinstance(result, Exception):
            log.warning("source %s failed: %s", name, result)
            continue
        log.info("source %s returned %d jobs", name, len(result))
        jobs.extend(result)
    return jobs


def run(
    config_path: Path = Path("config.yaml"),
    state_path: Path = Path("state/seen_jobs.json"),
) -> None:
    cfg = load_config(config_path)
    store = SeenStore(state_path)
    jobs = asyncio.run(fetch_all(cfg))

    log.info("fetched %d jobs total", len(jobs))

    client = None
    sent = 0
    for job in jobs:
        if not is_relevant(job, cfg.filters):
            continue
        if store.has(job.id):
            continue
        try:
            if client is None:
                client = get_client()
            draft = draft_pitch(job, cfg.profile, client=client)
        except Exception as e:
            log.warning("draft failed for %s: %s", job.id, e)
            draft = "(draft failed — reply manually)"
        build_cmd = None
        if is_website_job(job):
            try:
                queue_build(job)
                build_cmd = build_command(job)
            except Exception as e:
                log.warning("queue_build failed for %s: %s", job.id, e)
        try:
            send_job(job, draft, build_cmd=build_cmd)
            store.add(job.id)
            sent += 1
        except Exception as e:
            log.error("notify failed for %s: %s", job.id, e)

    store.save()
    log.info("done: sent %d alerts", sent)


if __name__ == "__main__":
    run()
