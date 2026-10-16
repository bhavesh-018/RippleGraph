import { useEffect, useState, useCallback } from "react";
import {
  Clock,
  RefreshCw,
  X,
  Search,
  Brain,
  Zap,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Minus,
} from "lucide-react";
import { api } from "../api/client";
import type { InvestigationSummary } from "../types";

interface HistoryPanelProps {
  onReplay: (summary: InvestigationSummary) => void;
  onClose: () => void;
  activeInvestigationId?: string | null;
}

// ── helpers ───────────────────────────────────────────────────────────────────

function formatRelative(iso: string): string {
  if (!iso) return "-";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function riskAccent(item: InvestigationSummary): string {
  if (item.incompatible_count > 0) return "#ef4444";
  if (item.at_risk_count > 0) return "#f97316";
  if (item.compatible_count > 0) return "#22c55e";
  return "#64748b";
}

function statusStyle(status: string, disconnected: boolean): { label: string; color: string; bg: string } {
  if (disconnected) return { label: "Proof Mode", color: "#a78bfa", bg: "rgba(167,139,250,0.1)" };
  if (status === "completed") return { label: "Complete", color: "#22c55e", bg: "rgba(34,197,94,0.1)" };
  if (status === "failed") return { label: "Failed", color: "#ef4444", bg: "rgba(239,68,68,0.1)" };
  return { label: status, color: "#94a3b8", bg: "rgba(148,163,184,0.08)" };
}

// ── component ─────────────────────────────────────────────────────────────────

export default function HistoryPanel({ onReplay, onClose, activeInvestigationId }: HistoryPanelProps) {
  const [items, setItems] = useState<InvestigationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [spinning, setSpinning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSpinning(true);
    try {
      const data = await api.getHistory(50);
      setItems(data.investigations);
      setTotal(data.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
      setTimeout(() => setSpinning(false), 600);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(
    (it) =>
      it.change_title.toLowerCase().includes(search.toLowerCase()) ||
      it.change_id.toLowerCase().includes(search.toLowerCase()) ||
      it.investigation_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={s.overlay} onClick={onClose}>
      <div style={s.modal} onClick={(e) => e.stopPropagation()}>

        {/* ── Header ── */}
        <div style={s.header}>
          <div style={s.headerLeft}>
            <Clock size={18} color="#6366f1" />
            <div>
              <h2 style={s.title}>Investigation History</h2>
              <span style={s.subtitle}>
                {loading ? "Loading..." : `${total} run${total !== 1 ? "s" : ""}`}
              </span>
            </div>
          </div>
          <button style={s.iconBtn} onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        {/* ── Search + Refresh ── */}
        <div style={s.toolbar}>
          <div style={s.searchWrap}>
            <Search size={14} color="#64748b" style={{ flexShrink: 0 }} />
            <input
              style={s.searchInput}
              placeholder="Search by ID, title, run ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button
            style={s.iconBtn}
            onClick={load}
            title="Refresh"
            aria-label="Refresh"
          >
            <RefreshCw
              size={14}
              style={{ transition: "transform 0.6s", transform: spinning ? "rotate(360deg)" : "rotate(0deg)" }}
            />
          </button>
        </div>

        {/* ── Column headers ── */}
        {!loading && !error && filtered.length > 0 && (
          <div style={s.colHeader}>
            <span style={{ flex: 1 }}>Change</span>
            <span style={{ width: 56, textAlign: "center" }}>Incomp.</span>
            <span style={{ width: 56, textAlign: "center" }}>At Risk</span>
            <span style={{ width: 56, textAlign: "center" }}>Compat.</span>
            <span style={{ width: 72, textAlign: "center" }}>Confidence</span>
            <span style={{ width: 60, textAlign: "right" }}>When</span>
            <span style={{ width: 20 }} />
          </div>
        )}

        {/* ── List ── */}
        <div style={s.list}>
          {loading && (
            <div style={s.stateBox}>
              <RefreshCw size={20} color="#6366f1" style={{ animation: "spin 1s linear infinite" }} />
              <span style={{ color: "#64748b", fontSize: 13 }}>Loading runs...</span>
            </div>
          )}

          {!loading && error && (
            <div style={s.stateBox}>
              <AlertCircle size={18} color="#ef4444" />
              <span style={{ color: "#ef4444", fontSize: 13 }}>{error}</span>
              <button style={s.textBtn} onClick={load}>Retry</button>
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div style={s.stateBox}>
              <Clock size={20} color="#334155" />
              <span style={{ color: "#475569", fontSize: 13 }}>
                {search ? "No runs match your search." : "No investigation runs yet."}
              </span>
            </div>
          )}

          {!loading && !error && filtered.map((item) => {
            const badge = statusStyle(item.status, item.disconnect_graph);
            const accent = riskAccent(item);
            const isActive = item.investigation_id === activeInvestigationId;

            return (
              <div
                key={item.investigation_id}
                style={{ ...s.row, ...(isActive ? s.rowActive : {}) }}
                onClick={() => onReplay(item)}
              >
                {/* left accent */}
                <div style={{ width: 3, alignSelf: "stretch", background: accent, borderRadius: 2, flexShrink: 0 }} />

                {/* change info */}
                <div style={{ flex: 1, minWidth: 0, paddingLeft: 10 }}>
                  <div style={s.rowTitle}>{item.change_title}</div>
                  <div style={s.rowMeta}>
                    <span style={{ color: "#6366f1", fontSize: 11, fontWeight: 600 }}>{item.change_id}</span>
                    <span style={s.dot} />
                    {item.memory_enabled
                      ? <><Brain size={11} color="#a78bfa" /><span>Memory</span></>
                      : <><Zap size={11} color="#64748b" /><span style={{ color: "#64748b" }}>Cold Start</span></>
                    }
                    <span style={s.dot} />
                    <span style={{ color: badge.color, background: badge.bg, padding: "1px 6px", borderRadius: 4, fontSize: 10, fontWeight: 600 }}>
                      {badge.label}
                    </span>
                    {isActive && (
                      <span style={s.activePill}>
                        <CheckCircle2 size={10} /> Active
                      </span>
                    )}
                  </div>
                </div>

                {/* stat columns */}
                <StatCell value={item.incompatible_count} color="#ef4444" Icon={AlertCircle} />
                <StatCell value={item.at_risk_count} color="#f97316" Icon={AlertTriangle} />
                <StatCell value={item.compatible_count} color="#22c55e" Icon={CheckCircle2} />
                <div style={{ ...s.statCell, width: 72 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#818cf8" }}>
                    {Math.round(item.avg_confidence * 100)}%
                  </span>
                </div>

                {/* when */}
                <div style={{ width: 60, textAlign: "right", fontSize: 11, color: "#475569", flexShrink: 0 }}>
                  {formatRelative(item.created_at)}
                </div>

                {/* chevron */}
                <div style={{ width: 20, display: "flex", alignItems: "center", justifyContent: "flex-end", flexShrink: 0 }}>
                  <ChevronRight size={14} color="#334155" />
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Footer ── */}
        <div style={s.footer}>
          <Minus size={12} color="#334155" />
          <span style={{ color: "#334155", fontSize: 11 }}>
            Click any row to replay its findings in the right panel
          </span>
        </div>
      </div>
    </div>
  );
}

function StatCell({ value, color, Icon }: { value: number; color: string; Icon: React.ElementType }) {
  return (
    <div style={{ ...s.statCell, width: 56 }}>
      {value > 0
        ? <><Icon size={11} color={color} /><span style={{ fontSize: 13, fontWeight: 600, color }}>{value}</span></>
        : <span style={{ fontSize: 13, color: "#1e293b" }}>0</span>
      }
    </div>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.5)",
    backdropFilter: "blur(3px)",
    zIndex: 1100,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  modal: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: 12,
    width: "min(820px, 95vw)",
    maxHeight: "85vh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px 20px",
    borderBottom: "1px solid #1e293b",
  },
  headerLeft: { display: "flex", alignItems: "center", gap: 10 },
  title: { margin: 0, fontSize: 15, fontWeight: 600, color: "#f1f5f9", lineHeight: 1.2 },
  subtitle: { fontSize: 11, color: "#475569", marginTop: 1, display: "block" },
  iconBtn: {
    background: "none",
    border: "1px solid #1e293b",
    color: "#64748b",
    borderRadius: 6,
    width: 30,
    height: 30,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  toolbar: {
    display: "flex",
    gap: 8,
    padding: "10px 20px",
    borderBottom: "1px solid #1e293b",
    alignItems: "center",
  },
  searchWrap: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "#1e293b",
    borderRadius: 6,
    padding: "6px 10px",
    border: "1px solid #334155",
  },
  searchInput: {
    flex: 1,
    background: "none",
    border: "none",
    color: "#cbd5e1",
    fontSize: 13,
    outline: "none",
    minWidth: 0,
  },
  colHeader: {
    display: "flex",
    alignItems: "center",
    padding: "6px 20px",
    gap: 8,
    borderBottom: "1px solid #1e293b",
    fontSize: 10,
    fontWeight: 600,
    color: "#334155",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  list: {
    flex: 1,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
  },
  stateBox: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    padding: "48px 0",
  },
  textBtn: {
    background: "none",
    border: "1px solid #1e293b",
    color: "#6366f1",
    borderRadius: 6,
    padding: "4px 12px",
    cursor: "pointer",
    fontSize: 12,
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 20px 10px 12px",
    borderBottom: "1px solid #0f172a",
    cursor: "pointer",
    transition: "background 0.12s",
    background: "transparent",
  },
  rowActive: {
    background: "rgba(99,102,241,0.06)",
    borderLeft: "none",
  },
  rowTitle: { fontSize: 13, color: "#e2e8f0", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  rowMeta: { display: "flex", alignItems: "center", gap: 6, marginTop: 3, fontSize: 11, color: "#a78bfa" },
  dot: { width: 3, height: 3, borderRadius: "50%", background: "#334155", flexShrink: 0 },
  activePill: {
    display: "flex",
    alignItems: "center",
    gap: 3,
    fontSize: 10,
    fontWeight: 600,
    color: "#22c55e",
    background: "rgba(34,197,94,0.1)",
    padding: "1px 6px",
    borderRadius: 4,
  },
  statCell: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    flexShrink: 0,
  },
  footer: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 20px",
    borderTop: "1px solid #1e293b",
    background: "#080f1a",
  },
};
