export interface QualityOption {
  id: number;
  label: string;
}

interface PlayerControlsProps {
  playing: boolean;
  onTogglePlay: () => void;
  qualities: QualityOption[];
  activeQualityId: number | null;
  onSelectQuality: (id: number) => void;
  buffering: boolean;
}

export default function PlayerControls({
  playing,
  onTogglePlay,
  qualities,
  activeQualityId,
  onSelectQuality,
  buffering,
}: PlayerControlsProps) {
  return (
    <div
      className="mono"
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "0.75rem",
        marginTop: "0.75rem",
        padding: "0.75rem 1rem",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 8,
      }}
    >
      <button
        type="button"
        onClick={onTogglePlay}
        style={{
          fontFamily: "inherit",
          cursor: "pointer",
          padding: "0.4rem 0.9rem",
          borderRadius: 6,
          border: "1px solid var(--accent)",
          background: "transparent",
          color: "var(--accent)",
        }}
      >
        {playing ? "Pause" : "Play"}
      </button>
      {buffering && (
        <span style={{ color: "var(--muted)", fontSize: "0.8rem" }} aria-live="polite">
          Buffering…
        </span>
      )}
      <label style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted)", fontSize: "0.8rem" }}>
        Quality
        <select
          className="mono"
          value={activeQualityId ?? ""}
          onChange={(e) => onSelectQuality(Number(e.target.value))}
          style={{
            background: "var(--bg)",
            color: "var(--text)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "0.35rem 0.5rem",
          }}
        >
          {qualities.map((q) => (
            <option key={q.id} value={q.id}>
              {q.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
