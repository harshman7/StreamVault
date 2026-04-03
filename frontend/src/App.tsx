import { Navigate, Route, Routes } from "react-router-dom";
import ContentGrid from "./components/ContentGrid";
import VideoPlayer from "./components/VideoPlayer";

export default function App() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          padding: "1rem 1.5rem",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "rgba(10,10,12,0.85)",
          backdropFilter: "blur(8px)",
        }}
      >
        <a href="/" style={{ fontWeight: 600, fontSize: "1.1rem", color: "var(--text)" }}>
          <span className="mono" style={{ color: "var(--accent)" }}>
            SV
          </span>
          <span style={{ marginLeft: 8 }}>StreamVault</span>
        </a>
        <span className="mono" style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
          dev OTT / HLS / AES-128
        </span>
      </header>
      <main style={{ flex: 1, padding: "1.5rem" }}>
        <Routes>
          <Route path="/" element={<ContentGrid />} />
          <Route path="/watch/:contentId" element={<VideoPlayer />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
