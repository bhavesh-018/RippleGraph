import { useState, useEffect } from 'react'
import {
  Play,
  Layers,
  BrainCircuit,
  GitCompare,
  History,
  Loader2,
} from 'lucide-react'
import type { ChangeProposal } from '../types'
import { api } from '../api/client'

interface LeftPanelProps {
  className?: string
  onRunInvestigation: (changeId: string, memoryEnabled: boolean) => void
  isRunning: boolean
  stage: string
  selectedChange?: ChangeProposal
  onSelectChange?: (change: ChangeProposal) => void
  onCompareMemory?: (changeId: string) => void
  onOpenHistory?: () => void
}

export default function LeftPanel({
  className = '',
  onRunInvestigation,
  isRunning,
  selectedChange,
  onSelectChange,
  onCompareMemory,
  onOpenHistory,
}: LeftPanelProps) {
  const [changes, setChanges] = useState<ChangeProposal[]>([])
  const [selectedId, setSelectedId] = useState('CHG-001')
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [loadingChanges, setLoadingChanges] = useState(true)

  useEffect(() => {
    async function loadChanges() {
      try {
        setLoadingChanges(true)
        const data = await api.getChanges()
        if (data && data.length > 0) {
          setChanges(data)
          setSelectedId(data[0].id)
          if (onSelectChange) {
            onSelectChange(data[0])
          }
        }
      } catch (err) {
        console.error('Failed to load change proposals:', err)
      } finally {
        setLoadingChanges(false)
      }
    }
    loadChanges()
  }, [])

  const currentChange = changes.find(c => c.id === selectedId) || selectedChange

  const handleSelect = (id: string) => {
    setSelectedId(id)
    const found = changes.find(c => c.id === id)
    if (found && onSelectChange) {
      onSelectChange(found)
    }
  }

  const handleRun = () => {
    if (!isRunning && currentChange) {
      onRunInvestigation(currentChange.id, memoryEnabled)
    }
  }



  // Risk badge color helper
  const getRiskColor = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case 'CRITICAL':
        return { bg: 'rgba(239, 68, 68, 0.2)', text: '#FCA5A5', border: '#EF4444' }
      case 'HIGH':
        return { bg: 'rgba(245, 158, 11, 0.2)', text: '#FCD34D', border: '#F59E0B' }
      case 'MEDIUM':
        return { bg: 'rgba(59, 130, 246, 0.2)', text: '#93C5FD', border: '#3B82F6' }
      case 'SAFE':
        return { bg: 'rgba(16, 185, 129, 0.2)', text: '#6EE7B7', border: '#10B981' }
      default:
        return { bg: '#27272A', text: '#A1A1AA', border: '#3F3F46' }
    }
  }

  const riskStyle = getRiskColor(currentChange?.risk_level || 'HIGH')

  return (
    <aside className={`left-panel ${className}`.trim()}>
      {/* Panel Header */}
      <div className="panel-header" style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={16} color="#A1A1AA" />
          <span className="text-primary font-semibold text-sm">Change Proposal</span>
        </div>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: '#71717A',
            background: '#18181B',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {changes.length} Proposals
        </span>
      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px 14px' }}>
        {/* Proposal Dropdown Selector */}
        <div>
          <label
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: '#A1A1AA',
              marginBottom: '6px',
              display: 'block',
            }}
          >
            Select Change Scenario
          </label>
          <select
            value={selectedId}
            onChange={(e) => handleSelect(e.target.value)}
            disabled={isRunning || loadingChanges}
            style={{
              width: '100%',
              padding: '9px 12px',
              background: '#141416',
              border: '1px solid #27272A',
              borderRadius: '8px',
              color: '#F4F4F5',
              fontSize: '12px',
              fontFamily: 'var(--font-sans)',
              cursor: 'pointer',
              outline: 'none',
              boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
            }}
          >
            {changes.map((c) => (
              <option key={c.id} value={c.id} style={{ background: '#18181B', color: '#F4F4F5' }}>
                [{c.id}] {c.title}
              </option>
            ))}
          </select>
        </div>

        {/* Change Details Card */}
        {currentChange && (
          <div
            style={{
              background: '#141416',
              border: '1px solid #27272A',
              borderRadius: '8px',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            {/* Header with Risk Pill */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#A1A1AA', fontWeight: 600 }}>
                {currentChange.id}
              </span>
              <span
                style={{
                  fontSize: '9px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  background: riskStyle.bg,
                  color: riskStyle.text,
                  border: `1px solid ${riskStyle.border}`,
                  padding: '2px 6px',
                  borderRadius: '4px',
                }}
              >
                {currentChange.risk_level}
              </span>
            </div>

            {/* Title */}
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#F4F4F5', lineHeight: 1.3 }}>
              {currentChange.title}
            </div>

            {/* Description */}
            <div style={{ fontSize: '11px', color: '#A1A1AA', lineHeight: 1.4 }}>
              {currentChange.description}
            </div>

            {/* Scope info */}
            <div
              style={{
                background: '#0D0D0F',
                border: '1px solid #1F1F23',
                borderRadius: '6px',
                padding: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '5px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#71717A' }}>Proposing:</span>
                <span style={{ color: '#E4E4E7' }}>{currentChange.proposing_service_name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#71717A' }}>Target API:</span>
                <span style={{ color: '#E4E4E7' }}>{currentChange.target_api_name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#71717A' }}>Proposed Contract:</span>
                <span style={{ color: '#818CF8' }}>{currentChange.proposed_contract_id}</span>
              </div>
            </div>

            {/* Claim Types Tags */}
            {currentChange.claim_types && currentChange.claim_types.length > 0 && (
              <div>
                <span style={{ fontSize: '10px', color: '#71717A', fontFamily: 'var(--font-mono)', display: 'block', marginBottom: '4px' }}>
                  Impacted Claim Keys:
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {currentChange.claim_types.map((claim) => (
                    <span
                      key={claim}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid #27272A',
                        borderRadius: '3px',
                        padding: '1px 5px',
                        fontSize: '10px',
                        fontFamily: 'var(--font-mono)',
                        color: '#A1A1AA',
                      }}
                    >
                      {claim}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Memory Engine Toggle (Track 2) */}
        <div
          style={{
            background: '#141416',
            border: '1px solid #27272A',
            borderRadius: '8px',
            padding: '10px 12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BrainCircuit size={14} color="#A78BFA" />
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#F4F4F5' }}>Agent Memory</span>
            </div>
            <button
              type="button"
              onClick={() => setMemoryEnabled(!memoryEnabled)}
              disabled={isRunning}
              style={{
                background: memoryEnabled ? 'rgba(16, 185, 129, 0.2)' : '#27272A',
                border: `1px solid ${memoryEnabled ? '#10B981' : '#3F3F46'}`,
                color: memoryEnabled ? '#6EE7B7' : '#A1A1AA',
                padding: '2px 7px',
                borderRadius: '12px',
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 200ms ease',
              }}
            >
              {memoryEnabled ? 'ON (FalkorDB)' : 'OFF (Cold Start)'}
            </button>
          </div>
          <p style={{ fontSize: '10.5px', color: '#71717A', lineHeight: 1.35, margin: 0 }}>
            {memoryEnabled
              ? 'Applies temporal decay formula e^(-0.05*dt) to prior findings in FalkorDB.'
              : 'Evaluates change in cold-start mode with zero historical context.'}
          </p>

          {/* Dual-Mode Memory Diff Trigger */}
          {onCompareMemory && (
            <button
              type="button"
              onClick={() => onCompareMemory(currentChange?.id || 'CHG-001')}
              disabled={isRunning}
              title="Compare Cold Start (OFF) vs FalkorDB Memory (ON) side-by-side"
              style={{
                marginTop: '10px',
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                background: 'rgba(167, 139, 250, 0.1)',
                border: '1px solid rgba(167, 139, 250, 0.3)',
                borderRadius: '6px',
                padding: '7px 10px',
                color: '#DDD6FE',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                cursor: isRunning ? 'not-allowed' : 'pointer',
                transition: 'all 150ms ease',
              }}
              onMouseEnter={(e) => {
                if (!isRunning) e.currentTarget.style.background = 'rgba(167, 139, 250, 0.22)'
              }}
              onMouseLeave={(e) => {
                if (!isRunning) e.currentTarget.style.background = 'rgba(167, 139, 250, 0.1)'
              }}
            >
              <GitCompare size={13} color="#A78BFA" />
              <span>Compare Memory Impact</span>
            </button>
          )}
        </div>
      </div>

      {/* Pinned Action Footer (Always visible without scrolling) */}
      <div
        style={{
          padding: '12px 14px',
          borderTop: '1px solid #1F1F1F',
          background: '#111111',
          flexShrink: 0,
        }}
      >
        <button
          type="button"
          onClick={handleRun}
          disabled={isRunning || !currentChange}
          style={{
            width: '100%',
            background: isRunning ? '#27272A' : '#EDEDED',
            border: '1px solid #3F3F46',
            borderRadius: '6px',
            padding: '10px 14px',
            color: isRunning ? '#71717A' : '#09090B',
            fontWeight: 600,
            fontSize: '12px',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            boxShadow: 'none',
            transition: 'all 150ms ease',
          }}
        >
          {isRunning ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Play size={14} fill="currentColor" />
          )}
          <span>{isRunning ? 'Simulating Rehearsal...' : 'Run Change Rehearsal'}</span>
        </button>

        {/* History Timeline button */}
        {onOpenHistory && (
          <button
            type="button"
            onClick={onOpenHistory}
            disabled={isRunning}
            title="View Investigation History Timeline"
            style={{
              marginTop: '8px',
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              background: 'rgba(99, 102, 241, 0.1)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              borderRadius: '6px',
              padding: '8px 14px',
              color: '#818CF8',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              cursor: isRunning ? 'not-allowed' : 'pointer',
              transition: 'all 150ms ease',
              opacity: isRunning ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              if (!isRunning) e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)'
            }}
            onMouseLeave={(e) => {
              if (!isRunning) e.currentTarget.style.background = 'rgba(99, 102, 241, 0.1)'
            }}
          >
            <History size={13} />
            <span>Investigation History</span>
          </button>
        )}
      </div>
    </aside>
  )
}
