from __future__ import annotations

import os
from datetime import datetime
from functools import wraps
from typing import Callable

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("VAP_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid api key")


def require_share_token(token: str | None, job_id: str) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="share token required")
    # Validation is performed by share store lookup in handlers.
