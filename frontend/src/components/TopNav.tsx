import { Network, Database, CheckCircle2, Loader2 } from 'lucide-react'
import type { ChangeProposal } from '../types'

interface TopNavProps {
  selectedChange?: ChangeProposal
  isRunning: boolean
  isComplete: boolean
  stage: string
  executionTimeMs?: number
  disconnectGraph?: boolean
  onToggleDisconnectGraph?: () => void
}

export default function TopNav({
  selectedChange,
  isRunning,
  isComplete,
  stage,
  executionTimeMs,
  disconnectGraph = false,
  onToggleDisconnectGraph,
}: TopNavProps) {
  const stages = [
    { id: 'investigator', name: 'Stage 1: Investigator' },
    { id: 'memory', name: 'Stage 2: Memory' },
    { id: 'reviewer', name: 'Stage 3: Reviewer' },
    { id: 'persist', name: 'Stage 4: Persist' },
  ]

  return (
    <header
      style={{
        height: '48px',
        borderBottom: '1px solid #1F1F23',
        background: '#0D0D0F',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        flexShrink: 0,
        zIndex: 10,
      }}
    >
      {/* Brand & Active Scenario */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '5px',
              background: '#18181B',
              border: '1px solid #27272A',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#EDEDED',
            }}
          >
            <Network size={14} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', letterSpacing: '-0.01em', color: '#EDEDED' }}>
              RippleGraph
            </span>
            <span
              style={{
                fontSize: '10px',
                color: '#71717A',
                fontFamily: 'var(--font-mono)',
                background: '#141416',
                border: '1px solid #27272A',
                padding: '1px 5px',
                borderRadius: '3px',
              }}
            >
              v1.0
            </span>
          </div>
        </div>

        <div style={{ width: '1px', height: '16px', background: '#27272A' }} />

        {/* Selected change badge */}
        {selectedChange && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                background: '#18181B',
                color: '#A1A1AA',
                padding: '2px 6px',
                borderRadius: '4px',
                border: '1px solid #27272A',
              }}
            >
              {selectedChange.id}
            </span>
            <span style={{ fontSize: '12px', color: '#E4E4E7', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedChange.title}
            </span>
          </div>
        )}
      </div>

      {/* 4-Stage Pipeline Progress Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {stages.map((s, index) => {
          const isCurrent = isRunning && stage.toLowerCase().includes(s.id)
          const isPassed = isComplete || (isRunning && index < 2)

          let badgeColor = '#52525B'
          let badgeBg = '#18181B'
          let borderColor = '#27272A'

          if (isCurrent) {
            badgeColor = '#67E8F9'
            badgeBg = 'rgba(6, 182, 212, 0.15)'
            borderColor = '#06B6D4'
          } else if (isPassed) {
            badgeColor = '#6EE7B7'
            badgeBg = 'rgba(16, 185, 129, 0.15)'
            borderColor = 'rgba(16, 185, 129, 0.3)'
          }

          return (
            <div
              key={s.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '3px 8px',
                borderRadius: '5px',
                border: `1px solid ${borderColor}`,
                background: badgeBg,
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                color: badgeColor,
                transition: 'all 200ms ease',
              }}
            >
              {isCurrent ? (
                <Loader2 size={12} className="animate-spin" />
              ) : isPassed ? (
                <CheckCircle2 size={12} />
              ) : (
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#3F3F46' }} />
              )}
              <span>{s.name}</span>
            </div>
          )
        })}

        {isComplete && executionTimeMs !== undefined && (
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: '#A1A1AA',
              marginLeft: '4px',
            }}
          >
            ({executionTimeMs.toFixed(1)}ms)
          </span>
        )}
      </div>

      {/* System Status Metrics / Proof Mode Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <button
          type="button"
          onClick={onToggleDisconnectGraph}
          title={
            disconnectGraph
              ? 'Click to re-connect FalkorDB graph reasoning'
              : 'Proof Mode: Click to simulate running without FalkorDB'
          }
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: disconnectGraph ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.1)',
            border: `1px solid ${disconnectGraph ? 'rgba(239, 68, 68, 0.35)' : 'rgba(16, 185, 129, 0.25)'}`,
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: disconnectGraph ? '#FCA5A5' : '#34D399',
            cursor: 'pointer',
            transition: 'all 150ms ease',
          }}
        >
          <Database size={12} color={disconnectGraph ? '#EF4444' : '#10B981'} />
          <span>{disconnectGraph ? 'FalkorDB: Offline' : 'FalkorDB: Connected'}</span>
          <span
            style={{
              fontSize: '9px',
              padding: '1px 5px',
              borderRadius: '3px',
              background: disconnectGraph ? '#7F1D1D' : '#064E3B',
              color: '#FFFFFF',
              fontWeight: 600,
              letterSpacing: '0.04em',
            }}
          >
            {disconnectGraph ? 'PROOF MODE' : 'ONLINE'}
          </span>
        </button>
      </div>
    </header>
  )
}
