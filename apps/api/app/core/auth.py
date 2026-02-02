from __future__ import annotations

import os

from fastapi import Header, HTTPException, Query


def require_api_key(
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None),
) -> None:
    expected = os.getenv("VAP_API_KEY")
    if not expected:
        return
    token = x_api_key or api_key
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="invalid api key")


def require_share_token(token: str | None, job_id: str) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="share token required")
    # Validation is performed by share store lookup in handlers.
