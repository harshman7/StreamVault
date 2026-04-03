#!/usr/bin/env python3
"""
Upload HLS output directory to S3 and optionally register catalog rows in PostgreSQL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config
import psycopg2


def load_meta(output_dir: Path) -> dict:
    meta_path = output_dir / "streamvault_meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Missing {meta_path} (run transcode.sh first)")
    return json.loads(meta_path.read_text())


def s3_client():
    kwargs = {
        "region_name": os.environ.get("AWS_REGION", "ca-central-1"),
        "config": Config(signature_version="s3v4"),
    }
    endpoint = os.environ.get("S3_ENDPOINT_URL") or None
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def upload_directory(client, bucket: str, local_dir: Path, prefix: str) -> list[str]:
    uploaded: list[str] = []
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(local_dir).as_posix()
        key = f"{prefix.strip('/')}/{rel}"
        extra = {}
        if rel.endswith(".m3u8"):
            extra["ContentType"] = "application/vnd.apple.mpegurl"
        elif rel.endswith(".ts"):
            extra["ContentType"] = "video/mp2t"
        client.upload_file(str(path), bucket, key, ExtraArgs=extra)
        uploaded.append(key)
    return uploaded


def upsert_catalog(conn, content_id: str, title: str, meta: dict) -> None:
    key_hex = meta["key_hex"]
    iv_hex = meta["iv_hex"]
    prefix = content_id
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO content (id, title, description, thumbnail_url, duration_seconds)
            VALUES (%s::uuid, %s, %s, NULL, NULL)
            ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title
            """,
            (content_id, title, "HLS VOD (ingested)"),
        )
        cur.execute("DELETE FROM rendition WHERE content_id = %s::uuid", (content_id,))
        cur.execute("DELETE FROM drm_key WHERE content_id = %s::uuid", (content_id,))
        for res, br, name in (
            ("1080p", 5000, "1080p.m3u8"),
            ("720p", 3000, "720p.m3u8"),
            ("480p", 1500, "480p.m3u8"),
        ):
            cur.execute(
                """
                INSERT INTO rendition (content_id, resolution, bitrate_kbps, s3_manifest_key)
                VALUES (%s::uuid, %s, %s, %s)
                """,
                (content_id, res, br, f"{prefix}/{name}"),
            )
        cur.execute(
            """
            INSERT INTO drm_key (content_id, key_hex, iv_hex)
            VALUES (%s::uuid, %s, %s)
            """,
            (content_id, key_hex, iv_hex),
        )
    conn.commit()


def main() -> int:
    p = argparse.ArgumentParser(description="Upload HLS segments to S3")
    p.add_argument("output_dir", type=Path, help="Directory containing master.m3u8 and segments")
    p.add_argument("--title", default="Untitled", help="Content title for catalog")
    p.add_argument("--skip-db", action="store_true", help="Only upload to S3")
    args = p.parse_args()

    output_dir = args.output_dir.resolve()
    if not output_dir.is_dir():
        print(f"Not a directory: {output_dir}", file=sys.stderr)
        return 1

    meta = load_meta(output_dir)
    content_id = meta["content_id"]
    bucket = os.environ.get("S3_BUCKET_NAME")
    if not bucket:
        print("S3_BUCKET_NAME is required", file=sys.stderr)
        return 1

    client = s3_client()
    keys = upload_directory(client, bucket, output_dir, content_id)
    print(f"Uploaded {len(keys)} objects under prefix {content_id}/")

    if not args.skip_db:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            print("DATABASE_URL not set; skipping DB registration (use --skip-db to silence)")
            return 0
        conn = psycopg2.connect(dsn)
        try:
            upsert_catalog(conn, content_id, args.title, meta)
            print(f"Catalog updated for content {content_id}")
        finally:
            conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
