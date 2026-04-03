# StreamVault

Portfolio-grade **mini OTT** stack: FFmpeg HLS packaging with **AES-128** segment encryption (key delivery like a simplified Widevine/FairPlay-style flow), a **FastAPI** manifest and metadata API backed by **PostgreSQL**, **AWS S3** storage with optional **CloudFront** signed URLs, and a **React + Shaka Player** dark UI for adaptive playback.

## Architecture (ASCII)

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌────────────┐
│  FFmpeg     │────▶│  S3 (segments +   │◀────│ CloudFront  │◀────│  Viewers   │
│ transcode   │     │  manifests)      │     │ (optional)  │     │  (browser) │
└─────────────┘     └────────▲─────────┘     └──────▲──────┘     └─────▲──────┘
       │                     │                      │                  │
       │              segment_uploader.py            │ signed URLs      │
       │                     │                      │ (optional)       │
       ▼                     │                      │                  │
┌──────────────────────────────────────────────────────────────────────────────┐
│                        FastAPI (manifest / content / drm)                     │
│   GET /manifest/{id}  → master.m3u8 (+ URL rewrite / CF signing)               │
│   GET /hls/{id}/*     → proxy segments/playlists from S3 (local-style CDN)     │
│   GET /drm/key/{id}   → 16-byte AES key (application/octet-stream)           │
│   GET /content        → catalog + renditions                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │ PostgreSQL   │
                                 └──────────────┘
```

## Tech stack

| Layer        | Technology                                      |
|-------------|--------------------------------------------------|
| Transcoding | FFmpeg, HLS, AES-128                             |
| API         | FastAPI, asyncpg, Pydantic, boto3                |
| Data        | PostgreSQL 15                                    |
| Frontend    | React, TypeScript, Vite, Axios, Shaka Player     |
| Delivery    | AWS S3, CloudFront (optional signed URLs)        |
| Orchestration | Docker Compose                               |

## Quick start

1. **Environment** — copy variables (optional but recommended for AWS):

   ```bash
   cp .env.example .env
   # Edit .env: S3_BUCKET_NAME, AWS keys, etc.
   ```

   Docker Compose reads `.env` automatically for variable substitution.

2. **Run the stack**

   ```bash
   docker compose up --build
   ```

   - API: [http://localhost:8000](http://localhost:8000) (`GET /health`)
   - UI: [http://localhost:3000](http://localhost:3000)

3. **Configure AWS** — set `S3_BUCKET_NAME` and credentials so the API can read manifests and segments. Without S3, the catalog may load but playback will fail until objects exist.

## Ingesting a video

Requires **FFmpeg** and **OpenSSL** on your machine (not only Docker). The FFmpeg graph expects **an audio track** on the input (stereo AAC per variant); silent inputs need a different filter graph.

1. Pick a stable **content UUID** (must match the database row you will create):

   ```bash
   export CONTENT_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
   mkdir -p ./media/out
   chmod +x ingestion/transcode.sh
   ```

2. **Transcode** (three ABR rungs, 6s segments, encrypted HLS):

   ```bash
   ./ingestion/transcode.sh ./your_video.mp4 ./media/out "$CONTENT_ID"
   ```

   - Writes `master.m3u8`, variant playlists, `.ts` segments, `enc.key`, and `streamvault_meta.json`.
   - `enc.keyinfo` uses `BACKEND_URL` (default `http://localhost:8000`) for the key URI embedded in playlists.

3. **Python uploader** (install deps on the host or in a venv):

   ```bash
   cd ingestion && pip install -r requirements.txt
   export AWS_REGION=ca-central-1
   export S3_BUCKET_NAME=your-bucket
   export DATABASE_URL=postgresql://postgres:password@localhost:5432/streamvault
   python segment_uploader.py ../media/out --title "My trailer"
   ```

   This uploads everything under `s3://$S3_BUCKET_NAME/$CONTENT_ID/` and upserts `content`, `rendition`, and `drm_key` rows.

4. Open the app, select the title, and play. Shaka resolves `EXT-X-KEY` against `/drm/key/{id}`; a request filter also forces the key URL to match `VITE_BACKEND_URL` / `BACKEND_URL` when needed.

## CloudFront signing

When `CLOUDFRONT_DOMAIN`, `CLOUDFRONT_KEY_PAIR_ID`, and `CLOUDFRONT_PRIVATE_KEY_PATH` are set, `/manifest/{id}` rewrites media URLs to **signed CloudFront URLs** instead of `/hls/...` proxy paths. See `infra/README.md` and `infra/s3_setup.py`.

## Project layout

- `ingestion/` — `transcode.sh`, `segment_uploader.py`
- `backend/` — FastAPI app
- `frontend/` — React + Shaka Player
- `db/init.sql` — schema
- `infra/` — S3 / CloudFront helpers


