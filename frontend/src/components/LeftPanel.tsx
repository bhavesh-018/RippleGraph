import { useState } from 'react'

// ── Available changes (matches seed data) ────────────────────────
const CHANGES = [
  { id: 'CHG-001', title: 'Breaking: sub → subject_id, roles → scopes' },
  { id: 'CHG-002', title: 'Transitional: Deploy cv-auth-v1-extended contract' },
]

interface LeftPanelProps {
  onRunInvestigation: (changeId: string, memoryEnabled: boolean) => void
  isRunning: boolean
  stage: string
}

export default function LeftPanel({ onRunInvestigation, isRunning, stage }: LeftPanelProps) {
  const [selectedChange, setSelectedChange] = useState(CHANGES[0].id)
  const [memoryEnabled, setMemoryEnabled] = useState(true)

  const handleRun = () => {
    if (!isRunning) {
      onRunInvestigation(selectedChange, memoryEnabled)
    }
  }

  return (
    <aside className="left-panel">
      <div className="panel-header">
        <span className="app-logo">RippleGraph</span>
      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* ── Change Selector ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label className="text-xs text-secondary font-medium" style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Proposed Change
          </label>
          <select
            value={selectedChange}
            onChange={(e) => setSelectedChange(e.target.value)}
            disabled={isRunning}
            style={{
              width: '100%',
              padding: '8px 10px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-active)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              fontFamily: 'var(--font-sans)',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {CHANGES.map(c => (
              <option key={c.id} value={c.id} style={{ background: '#141414' }}>
                {c.title}
              </option>
            ))}
          </select>
          <span className="text-xs text-muted" style={{ fontFamily: 'var(--font-mono)' }}>
            {selectedChange}
          </span>
        </div>

        {/* ── Memory Toggle ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label className="text-xs text-secondary font-medium" style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Prior Memory
          </label>
          <button
            onClick={() => setMemoryEnabled(!memoryEnabled)}
            disabled={isRunning}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 10px',
              background: memoryEnabled ? 'var(--status-compatible-bg)' : 'var(--bg-elevated)',
              border: `1px solid ${memoryEnabled ? 'var(--status-compatible-border)' : 'var(--border-active)'}`,
              borderRadius: 'var(--radius-md)',
              color: memoryEnabled ? 'var(--status-compatible-text)' : 'var(--text-muted)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              transition: 'all var(--transition-base)',
              outline: 'none',
            }}
          >
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: memoryEnabled ? 'var(--status-compatible-text)' : 'var(--text-muted)',
              transition: 'background var(--transition-base)',
            }} />
            {memoryEnabled ? 'ON' : 'OFF'}
          </button>
          <span className="text-xs text-muted">
            {memoryEnabled ? 'Uses findings from prior runs' : 'Cold start — no prior context'}
          </span>
        </div>

        {/* ── Run Button ── */}
        <button
          onClick={handleRun}
          disabled={isRunning}
          style={{
            width: '100%',
            padding: '10px',
            background: isRunning ? 'var(--bg-elevated)' : 'var(--text-primary)',
            color: isRunning ? 'var(--text-muted)' : 'var(--bg-root)',
            border: `1px solid ${isRunning ? 'var(--border-active)' : 'var(--text-primary)'}`,
            borderRadius: 'var(--radius-md)',
            fontSize: '13px',
            fontWeight: 600,
            fontFamily: 'var(--font-sans)',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            transition: 'all var(--transition-base)',
            letterSpacing: '-0.01em',
          }}
        >
          {isRunning ? (
            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
              <span className="pulse-dot" />
              Investigating...
            </span>
          ) : 'Run Investigation'}
        </button>

        {/* ── Stage Indicator ── */}
        {isRunning && stage && (
          <div style={{
            padding: '8px 10px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-subdued)',
            borderRadius: 'var(--radius-md)',
          }}>
            <span className="text-xs text-secondary font-medium" style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Active Stage
            </span>
            <p className="text-sm" style={{ color: 'var(--text-primary)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
              {stage}
            </p>
          </div>
        )}
      </div>
    </aside>
  )
}
