from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import DATA_DIR, DEFAULT_PROFILE
from app.core.jobs import JobStore
from app.core.pipeline import run_pipeline
from app.core.schemas import InputAsset, JobConfig, JobStatus
from app.core.storage import input_dir


async def main() -> None:
    store = JobStore(DATA_DIR)
    await store.load_from_disk()
    job = await store.create_job(JobConfig(profile=DEFAULT_PROFILE))

    input_path = input_dir(job.id) / "demo.txt"
    input_path.write_text("demo", encoding="utf-8")
    job.input = InputAsset(
        filename=input_path.name,
        content_type="text/plain",
        path=str(input_path),
    )
    job.status = JobStatus.processing
    job.stage = "seed"
    job.updated_at = datetime.now(timezone.utc)
    await store.update_job(job)

    manifest = await run_pipeline(job, input_path, on_update=store.update_job)
    job.manifest = manifest
    job.status = JobStatus.completed
    job.stage = "completed"
    job.updated_at = datetime.now(timezone.utc)
    await store.update_job(job)

    print(f"Seeded demo job: {job.id}")


if __name__ == "__main__":
    asyncio.run(main())
