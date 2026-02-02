from __future__ import annotations

import asyncio
from datetime import datetime, timezone
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
        self.subscriber_lock = asyncio.Lock()
        self.subscribers: set[asyncio.Queue] = set()
        self.job_subscribers: dict[str, set[asyncio.Queue]] = {}
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
        now = datetime.now(timezone.utc)
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
        await self.update_job(job)
        return job

    def start_job(self, job_id: str, input_path: Optional[Path]) -> None:
        asyncio.create_task(self.run_job(job_id, input_path))

    async def update_job(self, job: JobRecord) -> None:
        async with self.lock:
            self.jobs[job.id] = job
            await self.save_job(job)
            async with self.subscriber_lock:
                subscribers = list(self.subscribers)
                job_subscribers = list(self.job_subscribers.get(job.id, set()))
        payload = job.model_dump(mode="json")
        for queue in subscribers + job_subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                continue

    async def run_job(self, job_id: str, input_path: Optional[Path]) -> None:
        job = self.jobs[job_id]
        job.status = JobStatus.processing
        job.updated_at = datetime.now(timezone.utc)
        await self.update_job(job)
        try:
            manifest = await run_pipeline(job, input_path, on_update=self.update_job)
            job.manifest = manifest
            job.updated_at = datetime.now(timezone.utc)
            await self.update_job(job)
        except Exception as exc:
            job.status = JobStatus.failed
            job.error = str(exc)
            job.updated_at = datetime.now(timezone.utc)
            await self.update_job(job)

    async def list_jobs(self) -> list[JobRecord]:
        return sorted(self.jobs.values(), key=lambda item: item.created_at, reverse=True)

    async def get_job(self, job_id: str) -> JobRecord:
        return self.jobs[job_id]

    async def subscribe_all(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        async with self.subscriber_lock:
            self.subscribers.add(queue)
        return queue

    async def subscribe_job(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        async with self.subscriber_lock:
            self.job_subscribers.setdefault(job_id, set()).add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue, job_id: Optional[str] = None) -> None:
        async with self.subscriber_lock:
            if job_id:
                subscribers = self.job_subscribers.get(job_id)
                if subscribers and queue in subscribers:
                    subscribers.remove(queue)
            if queue in self.subscribers:
                self.subscribers.remove(queue)
