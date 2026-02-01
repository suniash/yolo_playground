from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .pipeline import run_pipeline
from .schemas import JobConfig, JobRecord, JobStatus
from .storage import job_file, load_json, save_json


class JobStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.jobs: dict[str, JobRecord] = {}
        self.lock = asyncio.Lock()
        self.worker_tasks: list[asyncio.Task] = []

    async def load_from_disk(self) -> None:
        jobs_root = self.data_dir / "jobs"
        if not jobs_root.exists():
            return
        for job_path in jobs_root.glob("*/job.json"):
            payload = load_json(job_path)
            record = JobRecord.model_validate(payload)
            self.jobs[record.id] = record

    async def save_job(self, job: JobRecord) -> None:
        save_json(job_file(job.id), job.model_dump())

    async def create_job(self, config: JobConfig) -> JobRecord:
        now = datetime.utcnow()
        job = JobRecord(
            id=uuid4().hex,
            status=JobStatus.queued,
            created_at=now,
            updated_at=now,
            progress=0.0,
            stage="queued",
            config=config,
        )
        self.jobs[job.id] = job
        await self.save_job(job)
        return job

    def start_job(self, job_id: str, input_path: Optional[Path]) -> None:
        asyncio.create_task(self.run_job(job_id, input_path))

    async def update_job(self, job: JobRecord) -> None:
        async with self.lock:
            self.jobs[job.id] = job
            await self.save_job(job)

    async def run_job(self, job_id: str, input_path: Optional[Path]) -> None:
        job = self.jobs[job_id]
        job.status = JobStatus.processing
        job.updated_at = datetime.utcnow()
        await self.update_job(job)
        try:
            manifest = await run_pipeline(job, input_path, on_update=self.update_job)
            job.manifest = manifest
            job.updated_at = datetime.utcnow()
            await self.update_job(job)
        except Exception as exc:
            job.status = JobStatus.failed
            job.error = str(exc)
            job.updated_at = datetime.utcnow()
            await self.update_job(job)

    async def list_jobs(self) -> list[JobRecord]:
        return sorted(self.jobs.values(), key=lambda item: item.created_at, reverse=True)

    async def get_job(self, job_id: str) -> JobRecord:
        return self.jobs[job_id]
