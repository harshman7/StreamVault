-- StreamVault PostgreSQL schema

CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rendition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    resolution TEXT NOT NULL,
    bitrate_kbps INTEGER NOT NULL,
    s3_manifest_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drm_key (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    key_hex TEXT NOT NULL,
    iv_hex TEXT NOT NULL,
    issued_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE playback_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ,
    user_agent TEXT,
    ip_address TEXT
);

CREATE INDEX idx_rendition_content ON rendition(content_id);
CREATE INDEX idx_drm_key_content ON drm_key(content_id);
CREATE INDEX idx_playback_content ON playback_session(content_id);
