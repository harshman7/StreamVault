from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RenditionOut(BaseModel):
    id: UUID
    resolution: str
    bitrate_kbps: int
    s3_manifest_key: str
    created_at: datetime | None = None


class ContentOut(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    created_at: datetime | None = None
    renditions: list[RenditionOut] = Field(default_factory=list)


class ContentListResponse(BaseModel):
    items: list[ContentOut]
