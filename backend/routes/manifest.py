from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response

import db
from s3 import cloudfront_enabled, get_object_bytes, get_signed_cloudfront_url

router = APIRouter(tags=["manifest"])

# Lines in a playlist that are standalone media URIs (not comments)
_URI_LINE = re.compile(r"^[\w./-]+\.(m3u8|ts)$")


def _rewrite_playlist_line(
    line: str,
    content_id: str,
    backend_base: str,
) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return line
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return line
    if _URI_LINE.match(stripped):
        rel = stripped
        if cloudfront_enabled():
            url = get_signed_cloudfront_url(f"{content_id}/{rel}", expiry_seconds=3600)
        else:
            url = f"{backend_base.rstrip('/')}/hls/{content_id}/{rel}"
        return url
    return line


def _rewrite_master_manifest(body: str, content_id: str, backend_base: str) -> str:
    out_lines = [_rewrite_playlist_line(line, content_id, backend_base) for line in body.splitlines()]
    text = "\n".join(out_lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def _master_key(content_id: str) -> str:
    return f"{content_id}/master.m3u8"


@router.get("/manifest/{content_id}")
async def get_master_manifest(content_id: UUID, request: Request) -> Response:
    row = await db.content_row(content_id)
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")

    from os import environ

    backend_base = (environ.get("BACKEND_URL") or "").strip().rstrip("/")
    if not backend_base:
        backend_base = str(request.base_url).rstrip("/")

    try:
        raw = get_object_bytes(_master_key(str(content_id)))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not load manifest from storage: {exc}") from exc

    body = raw.decode("utf-8", errors="replace")
    rewritten = _rewrite_master_manifest(body, str(content_id), backend_base)

    ua = request.headers.get("user-agent")
    client = request.client.host if request.client else None
    await db.log_playback_start(content_id, ua, client)

    return Response(
        content=rewritten,
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/hls/{content_id}/{path:path}")
async def proxy_hls_object(content_id: UUID, path: str) -> Response:
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    key = f"{content_id}/{path}"
    try:
        data = get_object_bytes(key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Object not found") from exc

    if path.endswith(".m3u8"):
        media_type = "application/vnd.apple.mpegurl"
    elif path.endswith(".ts"):
        media_type = "video/mp2t"
    else:
        media_type = "application/octet-stream"

    return Response(content=data, media_type=media_type, headers={"Cache-Control": "public, max-age=60"})
