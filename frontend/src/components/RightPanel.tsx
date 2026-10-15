import type { LogEntry } from '../api/sse'
import type { Finding } from '../types'

interface RightPanelProps {
  logs: LogEntry[]
  findings: Finding[]
  isRunning: boolean
  isComplete: boolean
}

function getStatusStyle(status: string) {
  switch (status?.toUpperCase()) {
    case 'INCOMPATIBLE':
      return { bg: 'var(--status-incompatible-badge)', text: 'var(--status-incompatible-text)' }
    case 'COMPATIBLE':
      return { bg: 'var(--status-compatible-badge)', text: 'var(--status-compatible-text)' }
    case 'POTENTIAL':
    case 'POTENTIAL_DOWNSTREAM':
      return { bg: 'var(--status-potential-badge)', text: 'var(--status-potential-text)' }
    default:
      return { bg: 'var(--border-subdued)', text: 'var(--text-secondary)' }
  }
}

function getLogColor(type: string) {
  switch (type) {
    case 'STAGE':    return 'var(--text-primary)'
    case 'STATUS':   return 'var(--status-potential-text)'
    case 'REVIEW':   return 'var(--status-incompatible-text)'
    case 'MEMORY':   return 'var(--status-compatible-text)'
    case 'COMPLETE': return 'var(--status-compatible-text)'
    case 'ERROR':    return 'var(--status-incompatible-text)'
    default:         return 'var(--text-muted)'
  }
}

export default function RightPanel({ logs, findings, isRunning, isComplete }: RightPanelProps) {
  // Summary counts
  const incompatible = findings.filter(f => f.status?.toLowerCase() === 'incompatible').length
  const potential = findings.filter(f => f.status?.toLowerCase().includes('potential')).length
  const compatible = findings.filter(f => f.status?.toLowerCase() === 'compatible').length

  return (
    <aside className="right-panel">
      {/* ── Header ── */}
      <div className="panel-header">
        <span className="text-primary font-semibold text-md">Findings</span>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {isRunning && (
            <span className="badge badge-default" style={{ fontSize: '9px' }}>LIVE</span>
          )}
          {isComplete && (
            <span className="badge badge-compatible" style={{ fontSize: '9px' }}>DONE</span>
          )}
        </div>
      </div>

      {/* ── Summary Bar ── */}
      {findings.length > 0 && (
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '8px 16px',
          borderBottom: '1px solid var(--border-subdued)',
          flexShrink: 0,
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: incompatible > 0 ? 'var(--status-incompatible-text)' : 'var(--text-muted)',
            fontWeight: incompatible > 0 ? 600 : 400,
          }}>
            {incompatible} INCOMPAT
          </span>
          <span style={{ color: 'var(--border-active)', fontSize: '10px' }}>·</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: potential > 0 ? 'var(--status-potential-text)' : 'var(--text-muted)',
            fontWeight: potential > 0 ? 600 : 400,
          }}>
            {potential} POTENTIAL
          </span>
          <span style={{ color: 'var(--border-active)', fontSize: '10px' }}>·</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: compatible > 0 ? 'var(--status-compatible-text)' : 'var(--text-muted)',
            fontWeight: compatible > 0 ? 600 : 400,
          }}>
            {compatible} COMPAT
          </span>
        </div>
      )}

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* ── Findings Cards ── */}
        {findings.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {findings.map(f => {
              const statusStyle = getStatusStyle(f.status)
              return (
                <div
                  key={f.id}
                  style={{
                    padding: '10px 12px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subdued)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    cursor: 'pointer',
                    transition: 'border-color var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-active)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subdued)')}
                >
                  {/* Title row */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="text-sm font-semibold">{f.service_name}</span>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '9px',
                      fontWeight: 500,
                      background: statusStyle.bg,
                      color: statusStyle.text,
                      padding: '1px 5px',
                      borderRadius: '3px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}>
                      {f.status}
                    </span>
                  </div>

                  {/* Summary */}
                  {f.summary && (
                    <p className="text-xs text-secondary" style={{ lineHeight: 1.4 }}>
                      {f.summary}
                    </p>
                  )}

                  {/* Confidence + category */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="text-xs text-muted" style={{ fontFamily: 'var(--font-mono)' }}>
                      {(f.confidence * 100).toFixed(0)}% confidence
                    </span>
                    <span className="text-xs text-muted">·</span>
                    <span className="text-xs text-muted" style={{ fontFamily: 'var(--font-mono)' }}>
                      {f.category}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* ── Empty state ── */}
        {findings.length === 0 && !isRunning && (
          <p className="text-muted text-sm">Run an investigation to see findings</p>
        )}

        {/* ── Live Log Console ── */}
        {logs.length > 0 && (
          <>
            <div className="divider" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span className="text-xs text-secondary font-medium" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>
                Event Log
              </span>
              <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1px' }}>
                {logs.map(log => (
                  <div key={log.id} style={{ display: 'flex', gap: '6px', padding: '2px 0', fontSize: '11px', fontFamily: 'var(--font-mono)', lineHeight: 1.4 }}>
                    <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>{log.timestamp}</span>
                    <span style={{ color: getLogColor(log.type), flexShrink: 0 }}>[{log.type}]</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
