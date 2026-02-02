from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .core.config import DATA_DIR, DEFAULT_PROFILE
from .core.auth import require_api_key
from .core.jobs import JobStore
from .core.pipeline import recompute_analytics
from .core.schemas import JobConfig, JobConfigUpdate, JobStatus
from .core.shares import ShareStore
from .core.storage import artifacts_dir, input_dir, job_file, load_json, save_json, shares_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = JobStore(DATA_DIR)
    await store.load_from_disk()
    app.state.store = store
    share_store = ShareStore(shares_file())
    await share_store.load()
    app.state.share_store = share_store
    yield


app = FastAPI(title="Vision Analytics Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/api/jobs")
async def list_jobs(_: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    jobs = await store.list_jobs()
    return [job.model_dump() for job in jobs]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, _: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    try:
        job = await store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    return job.model_dump()


@app.get("/api/jobs/{job_id}/config")
async def get_job_config(job_id: str, _: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    try:
        job = await store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    return job.config.model_dump()


@app.patch("/api/jobs/{job_id}/config")
async def update_job_config(job_id: str, payload: JobConfigUpdate, _: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    try:
        job = await store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        return job.config.model_dump()

    job.config = job.config.model_copy(update=updates)
    job.updated_at = datetime.utcnow()
    await store.update_job(job)
    return job.config.model_dump()


@app.post("/api/jobs")
async def create_job(
    video: Optional[UploadFile] = File(default=None),
    image: Optional[UploadFile] = File(default=None),
    config: Optional[str] = Form(default=None),
    _: None = Depends(require_api_key),
):
    store: JobStore = app.state.store

    if not video and not image:
        raise HTTPException(status_code=400, detail="video or image required")

    if config:
        try:
            config_payload = json.loads(config)
            job_config = JobConfig.model_validate(config_payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"invalid config json: {exc}")
    else:
        job_config = JobConfig(profile=DEFAULT_PROFILE)

    upload = video or image
    job = await store.create_job(job_config)

    input_path = input_dir(job.id) / upload.filename
    async with aiofiles.open(input_path, "wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            await handle.write(chunk)

    job.input = {
        "filename": upload.filename,
        "content_type": upload.content_type,
        "path": str(input_path),
    }
    job.updated_at = datetime.utcnow()
    await store.update_job(job)
    store.start_job(job.id, input_path)

    return job.model_dump()


@app.get("/api/jobs/{job_id}/input")
async def get_input(job_id: str, _: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    try:
        job = await store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")

    if not job.input:
        raise HTTPException(status_code=404, detail="input not available")

    return FileResponse(job.input["path"], media_type=job.input.get("content_type"), filename=job.input["filename"])


@app.get("/api/jobs/{job_id}/tracks")
async def get_tracks(job_id: str, _: None = Depends(require_api_key)):
    path = artifacts_dir(job_id) / "tracks.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="tracks not available")
    return JSONResponse(load_json(path))


@app.get("/api/jobs/{job_id}/metrics")
async def get_metrics(job_id: str, _: None = Depends(require_api_key)):
    path = artifacts_dir(job_id) / "metrics.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="metrics not available")
    return JSONResponse(load_json(path))


@app.get("/api/jobs/{job_id}/events")
async def get_events(job_id: str, _: None = Depends(require_api_key)):
    path = artifacts_dir(job_id) / "events.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="events not available")
    return JSONResponse(load_json(path))


@app.get("/api/jobs/{job_id}/manifest")
async def get_manifest(job_id: str, _: None = Depends(require_api_key)):
    path = artifacts_dir(job_id) / "manifest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="manifest not available")
    return JSONResponse(load_json(path))


@app.get("/api/jobs/{job_id}/artifacts/{artifact_name}")
async def download_artifact(job_id: str, artifact_name: str, _: None = Depends(require_api_key)):
    job_manifest_path = artifacts_dir(job_id) / "manifest.json"
    if not job_manifest_path.exists():
        raise HTTPException(status_code=404, detail="manifest not available")

    manifest = load_json(job_manifest_path)
    for item in manifest.get("items", []):
        if item.get("name") == artifact_name:
            return FileResponse(item["path"], media_type=item.get("content_type"), filename=Path(item["path"]).name)

    raise HTTPException(status_code=404, detail="artifact not found")


@app.post("/api/jobs/{job_id}/rerun")
async def rerun_analytics(job_id: str, payload: Optional[JobConfigUpdate] = None, _: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    try:
        job = await store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")

    if payload is not None:
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        if updates:
            job.config = job.config.model_copy(update=updates)

    series_path = artifacts_dir(job_id) / "series.json"
    if not series_path.exists():
        raise HTTPException(status_code=400, detail="series data not available")

    job.status = JobStatus.processing
    job.stage = "analytics"
    job.progress = 0.7
    job.updated_at = datetime.utcnow()
    await store.update_job(job)

    series = load_json(series_path)
    items, metrics, events = recompute_analytics(job.id, job.config, series)
    job.manifest.items = [item for item in job.manifest.items if item.name not in {"metrics", "events", "events_csv", "summary_csv", "report_html"}] + items
    job.summary["metrics"] = metrics["summary"]
    job.summary["events"] = len(events)
    job.status = JobStatus.completed
    job.stage = "completed"
    job.progress = 1.0
    job.updated_at = datetime.utcnow()
    await store.update_job(job)

    save_json(job_file(job.id), job.model_dump())

    return job.model_dump()


@app.post("/api/jobs/{job_id}/share")
async def create_share_link(job_id: str, ttl_hours: Optional[int] = None, _: None = Depends(require_api_key)):
    store: JobStore = app.state.store
    share_store: ShareStore = app.state.share_store
    try:
        await store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    link = await share_store.create(job_id, ttl_hours=ttl_hours)
    return link.model_dump()


@app.get("/api/share/{share_id}/job")
async def get_shared_job(share_id: str):
    share_store: ShareStore = app.state.share_store
    store: JobStore = app.state.store
    link = await share_store.get(share_id)
    if not link:
        raise HTTPException(status_code=404, detail="share link invalid")
    job = await store.get_job(link.job_id)
    return job.model_dump()


@app.get("/api/share/{share_id}/tracks")
async def get_shared_tracks(share_id: str):
    share_store: ShareStore = app.state.share_store
    link = await share_store.get(share_id)
    if not link:
        raise HTTPException(status_code=404, detail="share link invalid")
    path = artifacts_dir(link.job_id) / "tracks.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="tracks not available")
    return JSONResponse(load_json(path))


@app.get("/api/share/{share_id}/metrics")
async def get_shared_metrics(share_id: str):
    share_store: ShareStore = app.state.share_store
    link = await share_store.get(share_id)
    if not link:
        raise HTTPException(status_code=404, detail="share link invalid")
    path = artifacts_dir(link.job_id) / "metrics.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="metrics not available")
    return JSONResponse(load_json(path))


@app.get("/api/share/{share_id}/events")
async def get_shared_events(share_id: str):
    share_store: ShareStore = app.state.share_store
    link = await share_store.get(share_id)
    if not link:
        raise HTTPException(status_code=404, detail="share link invalid")
    path = artifacts_dir(link.job_id) / "events.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="events not available")
    return JSONResponse(load_json(path))


@app.get("/api/share/{share_id}/input")
async def get_shared_input(share_id: str):
    share_store: ShareStore = app.state.share_store
    store: JobStore = app.state.store
    link = await share_store.get(share_id)
    if not link:
        raise HTTPException(status_code=404, detail="share link invalid")
    job = await store.get_job(link.job_id)
    if not job.input:
        raise HTTPException(status_code=404, detail="input not available")
    return FileResponse(job.input["path"], media_type=job.input.get("content_type"), filename=job.input["filename"])
