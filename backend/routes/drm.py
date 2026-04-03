from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from db import fetch_drm_key

router = APIRouter(prefix="/drm", tags=["drm"])


@router.get("/key/{content_id}")
async def get_aes_key(content_id: UUID) -> Response:
    row = await fetch_drm_key(content_id)
    if not row:
        raise HTTPException(status_code=404, detail="No DRM key for this content")
    key_bytes, _iv_hex = row
    return Response(content=key_bytes, media_type="application/octet-stream")
