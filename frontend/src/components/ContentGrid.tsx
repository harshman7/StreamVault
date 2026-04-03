import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ContentItem } from "../types/content";

function formatDuration(sec: number | null | undefined): string {
  if (sec == null || sec <= 0) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export default function ContentGrid() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get<{ items: ContentItem[] }>("/content");
        if (!cancelled) {
          setItems(data.items);
          setErr(null);
        }
      } catch (e) {
        if (!cancelled) setErr("Could not load catalog. Is the API running?");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <p className="mono" style={{ color: "var(--muted)" }}>
        Loading catalog…
      </p>
    );
  }

  if (err) {
    return (
      <p className="mono" style={{ color: "#f87171" }}>
        {err}
      </p>
    );
  }

  if (!items.length) {
    return (
      <div className="mono" style={{ color: "var(--muted)", maxWidth: 520 }}>
        <p>No titles yet. Ingest a video with FFmpeg, upload to S3, then refresh.</p>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1.25rem" }}>Browse</h1>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "1rem",
        }}
      >
        {items.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => navigate(`/watch/${c.id}`)}
            style={{
              textAlign: "left",
              cursor: "pointer",
              borderRadius: 12,
              border: "1px solid var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
              padding: 0,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                aspectRatio: "16/9",
                background: "linear-gradient(145deg, #1f2937, #0f172a)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--muted)",
                fontSize: "0.75rem",
              }}
            >
              {c.thumbnail_url ? (
                <img
                  src={c.thumbnail_url}
                  alt=""
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : (
                <span className="mono">NO THUMB</span>
              )}
            </div>
            <div style={{ padding: "0.75rem 1rem" }}>
              <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{c.title}</div>
              <div className="mono" style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: 4 }}>
                {formatDuration(c.duration_seconds)} · {c.renditions.length} renditions
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
