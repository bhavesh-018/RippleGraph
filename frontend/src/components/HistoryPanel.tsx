import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import type { InvestigationSummary } from "../types";

interface HistoryPanelProps {
  onReplay: (summary: InvestigationSummary) => void;
  onClose: () => void;
  /** investigation_id currently shown in the graph, for highlight */
  activeInvestigationId?: string | null;
}

// -- helpers ------------------------------------------------------------------

function formatRelative(iso: string): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function statusBadge(status: string, disconnected: boolean) {
  if (disconnected)
    return { label: "Proof Mode", color: "#a78bfa", bg: "rgba(167,139,250,0.12)" };
  if (status === "completed")
    return { label: "Completed", color: "#34d399", bg: "rgba(52,211,153,0.12)" };
  if (status === "failed")
    return { label: "Failed", color: "#f87171", bg: "rgba(248,113,113,0.12)" };
  return { label: status, color: "#94a3b8", bg: "rgba(148,163,184,0.1)" };
}

function riskColor(item: InvestigationSummary): string {
  if (item.incompatible_count > 0) return "#f87171";
  if (item.at_risk_count > 0) return "#fb923c";
  if (item.compatible_count > 0) return "#34d399";
  return "#94a3b8";
}

function confidencePct(val: number): string {
  return `${Math.round(val * 100)}%`;
}

// -- component -----------------------------------------------------------------

export default function HistoryPanel({
  onReplay,
  onClose,
  activeInvestigationId,
}: HistoryPanelProps) {
  const [items, setItems] = useState<InvestigationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHistory(50);
      setItems(data.investigations);
      setTotal(data.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = items.filter(
    (it) =>
      it.change_title.toLowerCase().includes(search.toLowerCase()) ||
      it.change_id.toLowerCase().includes(search.toLowerCase()) ||
      it.investigation_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <span style={styles.headerIcon}>??</span>
            <div>
              <h2 style={styles.title}>Investigation History</h2>
              <p style={styles.subtitle}>
                {loading ? "Loading…" : `${total} run${total !== 1 ? "s" : ""} stored`}
              </p>
            </div>
          </div>
          <button style={styles.closeBtn} onClick={onClose} aria-label="Close">
            ?
          </button>
        </div>

        {/* Search */}
        <div style={styles.searchRow}>
          <input
            style={styles.searchInput}
            placeholder="Search by change ID, title, run ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button style={styles.refreshBtn} onClick={load} title="Refresh">
            ?
          </button>
        </div>

        {/* Body */}
        <div style={styles.list}>
          {loading && (
            <div style={styles.center}>
              <div style={styles.spinner} />
              <span style={{ color: "#64748b", marginLeft: 10 }}>Loading history…</span>
            </div>
          )}

          {!loading && error && (
            <div style={styles.center}>
              <span style={{ color: "#f87171" }}>? {error}</span>
              <button style={styles.retryBtn} onClick={load}>Retry</button>
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div style={styles.center}>
              <span style={{ color: "#475569", fontSize: 14 }}>
                {search ? "No runs match your search." : "No investigation runs yet."}
              </span>
            </div>
          )}

          {!loading && !error && filtered.map((item) => {
            const badge = statusBadge(item.status, item.disconnect_graph);
            const isActive = item.investigation_id === activeInvestigationId;
            const risk = riskColor(item);

            return (
              <div
                key={item.investigation_id}
                style={{
                  ...styles.card,
                  ...(isActive ? styles.cardActive : {}),
                }}
                onClick={() => onReplay(item)}
              >
                {/* Left accent bar */}
                <div style={{ ...styles.accentBar, background: risk }} />

                <div style={styles.cardBody}>
                  {/* Top row */}
                  <div style={styles.cardTop}>
                    <div style={styles.cardTitleGroup}>
                      <span style={styles.changeId}>{item.change_id}</span>
                      <span style={styles.changeTitle}>{item.change_title}</span>
                    </div>
                    <div style={styles.badgeGroup}>
                      {isActive && (
                        <span style={styles.activePill}>? Active</span>
                      )}
                      <span
                        style={{
                          ...styles.badge,
                          color: badge.color,
                          background: badge.bg,
                        }}
                      >
                        {badge.label}
                      </span>
                    </div>
                  </div>

                  {/* Stats row */}
                  <div style={styles.statsRow}>
                    <StatChip label="Incompatible" count={item.incompatible_count} color="#f87171" />
                    <StatChip label="At Risk" count={item.at_risk_count} color="#fb923c" />
                    <StatChip label="Compatible" count={item.compatible_count} color="#34d399" />
                    <StatChip label="Unaffected" count={item.unaffected_count} color="#64748b" />
                    <div style={styles.confidence}>
                      <span style={styles.confLabel}>Confidence</span>
                      <span style={styles.confValue}>{confidencePct(item.avg_confidence)}</span>
                    </div>
                  </div>

                  {/* Footer row */}
                  <div style={styles.footerRow}>
                    <span style={styles.meta}>
                      {item.memory_enabled ? "?? Memory ON" : "? Memory OFF"}
                    </span>
                    <span style={styles.meta}>
                      {item.findings_count} finding{item.findings_count !== 1 ? "s" : ""}
                    </span>
                    <span style={{ ...styles.meta, marginLeft: "auto" }}>
                      {formatRelative(item.created_at)}
                    </span>
                    <span style={styles.replayBtn}>Replay ?</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// -- sub-components ------------------------------------------------------------

function StatChip({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 56 }}>
      <span style={{ fontSize: 15, fontWeight: 700, color }}>{count}</span>
      <span style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </span>
    </div>
  );
}

// -- styles --------------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.55)",
    backdropFilter: "blur(4px)",
    zIndex: 1100,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  panel: {
    background: "linear-gradient(160deg, #0f172a 0%, #1e293b 100%)",
    border: "1px solid rgba(99,102,241,0.25)",
    borderRadius: 16,
    width: "min(760px, 94vw)",
    maxHeight: "88vh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    boxShadow: "0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(99,102,241,0.1)",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "20px 24px 16px",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },
  headerLeft: { display: "flex", alignItems: "center", gap: 14 },
  headerIcon: { fontSize: 28 },
  title: { margin: 0, fontSize: 18, fontWeight: 700, color: "#f1f5f9" },
  subtitle: { margin: 0, fontSize: 12, color: "#64748b", marginTop: 2 },
  closeBtn: {
    background: "none",
    border: "1px solid rgba(255,255,255,0.1)",
    color: "#94a3b8",
    borderRadius: 8,
    width: 32,
    height: 32,
    cursor: "pointer",
    fontSize: 14,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.15s",
  },
  searchRow: {
    display: "flex",
    gap: 8,
    padding: "14px 24px",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
  },
  searchInput: {
    flex: 1,
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 8,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "8px 12px",
    outline: "none",
  },
  refreshBtn: {
    background: "rgba(99,102,241,0.15)",
    border: "1px solid rgba(99,102,241,0.3)",
    color: "#818cf8",
    borderRadius: 8,
    width: 36,
    cursor: "pointer",
    fontSize: 18,
    fontWeight: 700,
    transition: "all 0.15s",
  },
  list: {
    flex: 1,
    overflowY: "auto",
    padding: "12px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  center: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: "48px 0",
  },
  spinner: {
    width: 24,
    height: 24,
    border: "3px solid rgba(99,102,241,0.2)",
    borderTop: "3px solid #818cf8",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  retryBtn: {
    background: "rgba(99,102,241,0.15)",
    border: "1px solid rgba(99,102,241,0.3)",
    color: "#818cf8",
    borderRadius: 8,
    padding: "6px 16px",
    cursor: "pointer",
    fontSize: 13,
  },
  card: {
    display: "flex",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 12,
    overflow: "hidden",
    cursor: "pointer",
    transition: "all 0.18s ease",
  },
  cardActive: {
    border: "1px solid rgba(99,102,241,0.5)",
    background: "rgba(99,102,241,0.07)",
    boxShadow: "0 0 0 1px rgba(99,102,241,0.2)",
  },
  accentBar: { width: 4, flexShrink: 0 },
  cardBody: { flex: 1, padding: "12px 16px", display: "flex", flexDirection: "column", gap: 8 },
  cardTop: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 },
  cardTitleGroup: { display: "flex", flexDirection: "column", gap: 2 },
  changeId: { fontSize: 10, color: "#6366f1", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
  changeTitle: { fontSize: 14, color: "#e2e8f0", fontWeight: 600, lineHeight: 1.3 },
  badgeGroup: { display: "flex", alignItems: "center", gap: 6, flexShrink: 0 },
  activePill: {
    fontSize: 10,
    color: "#34d399",
    background: "rgba(52,211,153,0.12)",
    border: "1px solid rgba(52,211,153,0.3)",
    borderRadius: 20,
    padding: "2px 8px",
    fontWeight: 600,
  },
  badge: {
    fontSize: 11,
    fontWeight: 600,
    borderRadius: 20,
    padding: "2px 10px",
    border: "1px solid transparent",
  },
  statsRow: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    padding: "8px 0",
    borderTop: "1px solid rgba(255,255,255,0.04)",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
  },
  confidence: { marginLeft: "auto", display: "flex", flexDirection: "column", alignItems: "flex-end" },
  confLabel: { fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: "0.04em" },
  confValue: { fontSize: 15, fontWeight: 700, color: "#818cf8" },
  footerRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  meta: { fontSize: 11, color: "#475569" },
  replayBtn: {
    fontSize: 11,
    color: "#6366f1",
    fontWeight: 600,
    letterSpacing: "0.03em",
    marginLeft: 8,
  },
};
