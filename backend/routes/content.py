from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import fetch_all_content, fetch_content
from models import ContentListResponse, ContentOut, RenditionOut

router = APIRouter(prefix="/content", tags=["content"])


def _group_rows(rows: list[dict]) -> list[ContentOut]:
    by_id: dict = {}
    renditions: dict = defaultdict(list)
    for r in rows:
        cid = r["id"]
        if cid not in by_id:
            by_id[cid] = {
                "id": cid,
                "title": r["title"],
                "description": r["description"],
                "thumbnail_url": r["thumbnail_url"],
                "duration_seconds": r["duration_seconds"],
                "created_at": r["created_at"],
            }
        if r.get("rid"):
            renditions[cid].append(
                RenditionOut(
                    id=r["rid"],
                    resolution=r["resolution"],
                    bitrate_kbps=r["bitrate_kbps"],
                    s3_manifest_key=r["s3_manifest_key"],
                    created_at=r["rcreated"],
                )
            )
    return [
        ContentOut(**{**by_id[cid], "renditions": renditions[cid]})
        for cid in by_id
    ]


@router.get("", response_model=ContentListResponse)
async def list_content() -> ContentListResponse:
    rows = await fetch_all_content()
    return ContentListResponse(items=_group_rows(rows))


@router.get("/{content_id}", response_model=ContentOut)
async def get_content(content_id: UUID) -> ContentOut:
    rows = await fetch_content(content_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Content not found")
    grouped = _group_rows(rows)
    return grouped[0]
