"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "online" | "offline" | "degraded";

const statusConfig: Record<Status, { color: string; label: string }> = {
  checking: { color: "var(--text-muted)", label: "Checking…" },
  online: { color: "var(--success)", label: "Online" },
  degraded: { color: "var(--warning)", label: "Degraded" },
  offline: { color: "var(--error)", label: "Offline" },
};

export default function SystemStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"}/health/ready`,
          { signal: AbortSignal.timeout(4000) }
        );
        const data = await res.json();
        setStatus(data.status === "ready" ? "online" : "degraded");
      } catch {
        setStatus("offline");
      }
    };

    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  const cfg = statusConfig[status];

  return (
    <div
      id="system-status"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "5px 12px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        fontSize: "12px",
        color: "var(--text-secondary)",
      }}
    >
      <div
        style={{
          width: "7px",
          height: "7px",
          borderRadius: "50%",
          background: cfg.color,
          boxShadow: status === "online" ? `0 0 6px ${cfg.color}` : "none",
          transition: "all 0.3s",
        }}
      />
      <span>Backend: {cfg.label}</span>
    </div>
  );
}
