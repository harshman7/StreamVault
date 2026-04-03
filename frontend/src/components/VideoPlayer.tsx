import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import shaka from "shaka-player";
import { getBackendOrigin } from "../api/client";
import { useManifestUrl } from "../hooks/useManifest";
import PlayerControls, { type QualityOption } from "./PlayerControls";

export default function VideoPlayer() {
  const { contentId } = useParams<{ contentId: string }>();
  const manifestUrl = useManifestUrl(contentId);
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<shaka.Player | null>(null);
  const tracksRef = useRef<Map<number, shaka.extern.Track>>(new Map());

  const [error, setError] = useState<string | null>(null);
  const [buffering, setBuffering] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [qualities, setQualities] = useState<QualityOption[]>([]);
  const [activeQualityId, setActiveQualityId] = useState<number | null>(null);

  const drmKeyPattern = useCallback(
    (uri: string) => {
      const base = getBackendOrigin();
      return uri.includes("/drm/key/") || uri.startsWith(`${base}/drm/key/`);
    },
    []
  );

  useEffect(() => {
    if (!contentId || !manifestUrl) return;
    const video = videoRef.current;
    if (!video) return;

    shaka.polyfill.installAll();
    if (!shaka.Player.isBrowserSupported()) {
      setError("Browser not supported for Shaka Player");
      return;
    }

    const player = new shaka.Player(video);
    playerRef.current = player;

    // HLS AES-128: playlists reference EXT-X-KEY URI; normalize host to match dev proxy / env.
    const drmBase = `${getBackendOrigin()}/drm/key/${contentId}`;

    const net = player.getNetworkingEngine();
    if (net) {
      net.registerRequestFilter((_type, request, _context) => {
        const uris = request.uris;
        if (!uris?.length) return;
        const u = uris[0];
        if (drmKeyPattern(u)) {
          request.uris[0] = drmBase;
        }
      });
    }

    const onBuffering = (e: Event) => {
      const fe = e as shaka.util.FakeEvent & { buffering?: boolean };
      setBuffering(Boolean(fe.buffering));
    };
    video.addEventListener("play", () => setPlaying(true));
    video.addEventListener("pause", () => setPlaying(false));
    player.addEventListener("buffering", onBuffering);

    const buildQualities = () => {
      const tracks = player.getVariantTracks();
      const active = tracks.find((t) => t.active);
      const map = new Map<number, shaka.extern.Track>();
      const opts: QualityOption[] = tracks.map((t, i) => {
        const id = i;
        map.set(id, t);
        const h = t.height || 0;
        const label =
          h >= 1080 ? "1080p" : h >= 720 ? "720p" : h >= 480 ? "480p" : `${h}p`;
        return { id, label: `${label} · ${Math.round(t.bandwidth / 1000)} kbps` };
      });
      tracksRef.current = map;
      setQualities(opts);
      if (active) {
        const idx = tracks.indexOf(active);
        if (idx >= 0) setActiveQualityId(idx);
      }
    };

    player.addEventListener("trackschanged", buildQualities);
    player.addEventListener("adaptation", buildQualities);

    player
      .load(manifestUrl)
      .then(() => {
        setError(null);
        buildQualities();
        setBuffering(false);
      })
      .catch((err: unknown) => {
        console.error(err);
        setError(err instanceof Error ? err.message : "Playback failed");
        setBuffering(false);
      });

    return () => {
      player.removeEventListener("buffering", onBuffering);
      player.removeEventListener("trackschanged", buildQualities);
      player.removeEventListener("adaptation", buildQualities);
      player.destroy();
      playerRef.current = null;
      tracksRef.current.clear();
    };
  }, [contentId, manifestUrl, drmKeyPattern]);

  const handleTogglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
  };

  const handleSelectQuality = (id: number) => {
    const player = playerRef.current;
    const track = tracksRef.current.get(id);
    if (!player || !track) return;
    player.selectVariantTrack(track, true);
    setActiveQualityId(id);
  };

  if (!contentId) {
    return <p style={{ color: "var(--muted)" }}>Missing content id.</p>;
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      <p className="mono" style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "1rem" }}>
        <Link to="/">← Catalog</Link>
        <span style={{ marginLeft: 12 }}>content_id: {contentId}</span>
      </p>
      <div
        style={{
          position: "relative",
          borderRadius: 12,
          overflow: "hidden",
          border: "1px solid var(--border)",
          background: "#000",
          aspectRatio: "16 / 9",
        }}
      >
        <video
          ref={videoRef}
          controls
          playsInline
          style={{ width: "100%", height: "100%", display: "block" }}
        />
        {buffering && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              pointerEvents: "none",
              background: "rgba(0,0,0,0.35)",
            }}
            aria-hidden
          >
            <div
              className="mono"
              style={{
                width: 48,
                height: 48,
                border: "3px solid var(--border)",
                borderTopColor: "var(--accent)",
                borderRadius: "50%",
                animation: "sv-spin 0.9s linear infinite",
              }}
            />
          </div>
        )}
        <style>{`@keyframes sv-spin { to { transform: rotate(360deg); } }`}</style>
      </div>
      <PlayerControls
        playing={playing}
        onTogglePlay={handleTogglePlay}
        qualities={qualities}
        activeQualityId={activeQualityId}
        onSelectQuality={handleSelectQuality}
        buffering={buffering}
      />
      {error && (
        <p className="mono" style={{ color: "#f87171", marginTop: "1rem", fontSize: "0.9rem" }}>
          {error}
        </p>
      )}
    </div>
  );
}
