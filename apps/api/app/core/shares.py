from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from .schemas import ShareLink
from .storage import load_json, save_json


class ShareStore:
    def __init__(self, path):
        self.path = path
        self.items: dict[str, ShareLink] = {}

    async def load(self) -> None:
        if not self.path.exists():
            return
        payload = load_json(self.path)
        for item in payload.get("items", []):
            link = ShareLink.model_validate(item)
            self.items[link.id] = link

    async def save(self) -> None:
        save_json(self.path, {"items": [item.model_dump() for item in self.items.values()]})

    async def create(self, job_id: str, ttl_hours: Optional[int] = None) -> ShareLink:
        expires_at = None
        if ttl_hours:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        link = ShareLink(id=uuid4().hex, job_id=job_id, created_at=datetime.utcnow(), expires_at=expires_at)
        self.items[link.id] = link
        await self.save()
        return link

    async def get(self, link_id: str) -> Optional[ShareLink]:
        link = self.items.get(link_id)
        if not link:
            return None
        if link.expires_at and link.expires_at < datetime.utcnow():
            return None
        return link
