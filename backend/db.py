from __future__ import annotations

import os
from typing import Any
from uuid import UUID

import asyncpg

_pool: asyncpg.Pool | None = None


async def connect() -> None:
    global _pool
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)


async def disconnect() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


async def log_playback_start(
    content_id: UUID,
    user_agent: str | None,
    ip_address: str | None,
) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO playback_session (content_id, user_agent, ip_address)
            VALUES ($1, $2, $3)
            """,
            content_id,
            user_agent,
            ip_address,
        )


async def fetch_all_content() -> list[dict[str, Any]]:
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id, c.title, c.description, c.thumbnail_url, c.duration_seconds, c.created_at,
                   r.id AS rid, r.resolution, r.bitrate_kbps, r.s3_manifest_key, r.created_at AS rcreated
            FROM content c
            LEFT JOIN rendition r ON r.content_id = c.id
            ORDER BY c.created_at DESC, r.bitrate_kbps DESC NULLS LAST
            """
        )
    return [dict(r) for r in rows]


async def fetch_content(content_id: UUID) -> list[dict[str, Any]]:
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id, c.title, c.description, c.thumbnail_url, c.duration_seconds, c.created_at,
                   r.id AS rid, r.resolution, r.bitrate_kbps, r.s3_manifest_key, r.created_at AS rcreated
            FROM content c
            LEFT JOIN rendition r ON r.content_id = c.id
            WHERE c.id = $1
            ORDER BY r.bitrate_kbps DESC NULLS LAST
            """,
            content_id,
        )
    return [dict(r) for r in rows]


async def content_row(content_id: UUID) -> dict[str, Any] | None:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, title, description, thumbnail_url, duration_seconds, created_at FROM content WHERE id = $1",
            content_id,
        )
    return dict(row) if row else None


async def fetch_drm_key(content_id: UUID) -> tuple[bytes, str] | None:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT key_hex, iv_hex FROM drm_key WHERE content_id = $1 ORDER BY issued_at DESC LIMIT 1",
            content_id,
        )
    if not row:
        return None
    key_hex = row["key_hex"]
    raw = bytes.fromhex(key_hex.replace(" ", ""))
    return raw, row["iv_hex"]
