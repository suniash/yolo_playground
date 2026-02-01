from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def jobs_root() -> Path:
    return ensure_dir(DATA_DIR / "jobs")


def job_dir(job_id: str) -> Path:
    return ensure_dir(jobs_root() / job_id)


def job_file(job_id: str) -> Path:
    return job_dir(job_id) / "job.json"


def input_dir(job_id: str) -> Path:
    return ensure_dir(job_dir(job_id) / "input")


def artifacts_dir(job_id: str) -> Path:
    return ensure_dir(job_dir(job_id) / "artifacts")


def exports_dir(job_id: str) -> Path:
    return ensure_dir(job_dir(job_id) / "exports")


def save_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0
