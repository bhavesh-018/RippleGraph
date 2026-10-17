import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  ShieldCheck,
  FilterX,
  Sparkles,
  Clock,
  Loader2,
} from 'lucide-react'
import type { Finding, RedHerring } from '../types'

interface RightPanelProps {
  findings: Finding[]
  redHerrings?: RedHerring[]
  isRunning: boolean
  isComplete: boolean
  selectedServiceId?: string
  onSelectService?: (serviceId: string) => void
  summary?: {
    incompatible: number
    potential_downstream: number
    compatible: number
    unaffected: number
  }
  disconnectGraph?: boolean
  investigationId?: string
  onInspectFinding?: (f: Finding) => void
}

export default function RightPanel({
  findings,
  redHerrings = [],
  isRunning,
  isComplete,
  selectedServiceId,
  onSelectService,
  summary,
  disconnectGraph = false,
  investigationId,
  onInspectFinding,
}: RightPanelProps) {
  const incompatibleCount = summary?.incompatible ?? findings.filter(f => f.status?.toLowerCase() === 'incompatible').length
  const potentialCount = summary?.potential_downstream ?? findings.filter(f => f.status?.toLowerCase().includes('potential')).length
  const compatibleCount = summary?.compatible ?? findings.filter(f => f.status?.toLowerCase() === 'compatible').length

  return (
    <aside className="right-panel">
      {/* Panel Header */}
      <div className="panel-header" style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} color="#A1A1AA" />
          <span className="text-primary font-semibold text-sm">Blast Radius & Findings</span>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {isRunning && (
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '9px',
                fontWeight: 700,
                background: 'rgba(6, 182, 212, 0.2)',
                color: '#67E8F9',
                padding: '2px 6px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Loader2 size={10} className="animate-spin" />
              INVESTIGATING
            </span>
          )}
          {isComplete && (
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '9px',
                fontWeight: 700,
                background: 'rgba(16, 185, 129, 0.2)',
                color: '#6EE7B7',
                padding: '2px 6px',
                borderRadius: '4px',
              }}
            >
              VERIFIED
            </span>
          )}
          {isComplete && investigationId && (
            <button
              onClick={() => window.open(`/api/investigations/${investigationId}/checklist`)}
              title="Download mitigation checklist as Markdown"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                background: 'rgba(99,102,241,0.12)',
                border: '1px solid rgba(99,102,241,0.3)',
                borderRadius: '4px',
                padding: '2px 7px',
                cursor: 'pointer',
                color: '#A5B4FC',
                fontFamily: 'var(--font-mono)',
                fontSize: '9px',
                fontWeight: 700,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                transition: 'background 150ms ease',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(99,102,241,0.25)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(99,102,241,0.12)')}
            >
              ⬇ Export Plan
            </button>
          )}
        </div>
      </div>

      {/* Summary Scoreboard Bar */}
      {findings.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 16px',
            background: '#0D0D0F',
            borderBottom: '1px solid #1F1F23',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#FCA5A5' }}>
            <AlertOctagon size={12} />
            <span style={{ fontWeight: 700 }}>{incompatibleCount}</span>
            <span style={{ color: '#71717A' }}>Breaking</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#FCD34D' }}>
            <AlertTriangle size={12} />
            <span style={{ fontWeight: 700 }}>{potentialCount}</span>
            <span style={{ color: '#71717A' }}>Downstream</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#6EE7B7' }}>
            <CheckCircle2 size={12} />
            <span style={{ fontWeight: 700 }}>{compatibleCount}</span>
            <span style={{ color: '#71717A' }}>Safe</span>
          </div>
        </div>
      )}

      {/* Panel Body */}
      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {findings.length === 0 ? (
          <div
            style={{
              padding: '40px 16px',
              textAlign: 'center',
              color: '#71717A',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <ShieldCheck size={32} color={disconnectGraph ? '#EF4444' : '#3F3F46'} />
            <div style={{ fontSize: '13px', fontWeight: 500, color: disconnectGraph ? '#FCA5A5' : '#A1A1AA' }}>
              {disconnectGraph ? 'Proof Mode Active (FalkorDB Disconnected)' : 'No Active Investigation'}
            </div>
            <p style={{ fontSize: '11px', lineHeight: 1.4, margin: 0, color: disconnectGraph ? '#F87171' : '#71717A' }}>
              {disconnectGraph
                ? 'FalkorDB is offline. Click "Run Change Rehearsal" to demonstrate how non-graph systems suffer from 0-hop dependency blind spots.'
                : 'Select a proposed change on the left and click "Run Change Rehearsal" to simulate the multi-hop blast radius.'}
            </p>
          </div>
        ) : (
          <>
            {/* Proof Mode Audit Banner */}
            {disconnectGraph && (
              <div
                style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid #7F1D1D',
                  borderRadius: '8px',
                  padding: '10px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#F87171' }}>
                  <AlertTriangle size={14} />
                  <span style={{ fontWeight: 700, fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                    FALKORDB REASONING OFFLINE (PROOF MODE)
                  </span>
                </div>
                <p style={{ fontSize: '11px', color: '#FCA5A5', lineHeight: 1.35, margin: 0 }}>
                  Flat table lookups failed to discover any multi-hop consumers. Without FalkorDB index-free adjacency, recursive blast radius cannot be traversed.
                </p>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: '#EF4444', lineHeight: 1.4 }}>
                  <div>- 0 breaking consumers detected (Blind Spot)</div>
                  <div>- 0 contract compatibility rules evaluated</div>
                  <div>- 0 prior findings recalled from memory</div>
                </div>
              </div>
            )}

            {/* Findings List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {findings.map((finding) => {
                const isSelected = finding.service_id === selectedServiceId
                const isBreaking = finding.status?.toLowerCase() === 'incompatible'
                const isPotential = finding.status?.toLowerCase().includes('potential')
                const isCompatible = finding.status?.toLowerCase() === 'compatible'

                let cardBorder = '#27272A'
                let badgeBg = '#18181B'
                let badgeText = '#A1A1AA'
                let badgeLabel = finding.status.toUpperCase()

                if (isBreaking) {
                  cardBorder = isSelected ? '#EF4444' : '#3F1D1D'
                  badgeBg = 'rgba(239, 68, 68, 0.2)'
                  badgeText = '#FCA5A5'
                  badgeLabel = 'BREAKING'
                } else if (isPotential) {
                  cardBorder = isSelected ? '#F59E0B' : '#382810'
                  badgeBg = 'rgba(245, 158, 11, 0.2)'
                  badgeText = '#FCD34D'
                  badgeLabel = 'POTENTIAL RISK'
                } else if (isCompatible) {
                  cardBorder = isSelected ? '#10B981' : '#142918'
                  badgeBg = 'rgba(16, 185, 129, 0.2)'
                  badgeText = '#6EE7B7'
                  badgeLabel = 'COMPATIBLE'
                }

                const confPercent = Math.round(finding.confidence * 100)

                return (
                  <div
                    key={finding.id}
                    className="finding-card-appear"
                    onClick={() => onSelectService && onSelectService(finding.service_id)}
                    style={{
                      background: '#141416',
                      border: `1px solid ${cardBorder}`,
                      borderRadius: '8px',
                      padding: '12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      cursor: 'pointer',
                      transition: 'all 200ms ease',
                      boxShadow: isSelected ? '0 0 12px rgba(255, 255, 255, 0.1)' : 'none',
                    }}
                  >
                    {/* Header: Service Name + Status Badge */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: '#F4F4F5' }}>
                        {finding.service_name || finding.service_id}
                      </span>
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 700,
                          fontFamily: 'var(--font-mono)',
                          letterSpacing: '0.04em',
                          background: badgeBg,
                          color: badgeText,
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        {badgeLabel}
                      </span>
                    </div>

                    {/* Category & Hop Depth */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '11px',
                        color: '#71717A',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      <span>{finding.category}</span>
                      {finding.hop_depth !== undefined && (
                        <>
                          <span>•</span>
                          <span>Hop {finding.hop_depth}</span>
                        </>
                      )}
                    </div>

                    {/* Confidence Meter */}
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '10px',
                          fontFamily: 'var(--font-mono)',
                          color: '#A1A1AA',
                          marginBottom: '3px',
                        }}
                      >
                        <span>Agent Confidence:</span>
                        <span style={{ fontWeight: 600, color: '#F4F4F5' }}>{confPercent}%</span>
                      </div>
                      <div
                        style={{
                          width: '100%',
                          height: '4px',
                          background: '#27272A',
                          borderRadius: '2px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${confPercent}%`,
                            height: '100%',
                            background: isBreaking ? '#EF4444' : isPotential ? '#F59E0B' : '#10B981',
                            borderRadius: '2px',
                          }}
                        />
                      </div>
                    </div>

                    {/* Memory Reaffirmation Badge */}
                    {finding.reaffirmed && (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          fontSize: '10px',
                          background: 'rgba(16, 185, 129, 0.12)',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          borderRadius: '4px',
                          padding: '3px 8px',
                          color: '#6EE7B7',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 600,
                        }}
                      >
                        <Sparkles size={11} />
                        <span>MEMORY RE-AFFIRMED</span>
                        <span style={{ color: '#A1A1AA', fontWeight: 400 }}>• Boosted to {confPercent}%</span>
                      </div>
                    )}

                    {/* Stale Finding Warning */}
                    {finding.is_stale && (
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '3px',
                          background: 'rgba(245, 158, 11, 0.12)',
                          border: '1px solid rgba(245, 158, 11, 0.3)',
                          borderRadius: '4px',
                          padding: '4px 8px',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            fontSize: '10px',
                            color: '#FCD34D',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 600,
                          }}
                        >
                          <AlertTriangle size={11} />
                          <span>STALE FINDING RESOLVED</span>
                        </div>
                        {finding.staleness_reason && (
                          <div style={{ fontSize: '10px', color: '#FDE68A', lineHeight: 1.3 }}>
                            {finding.staleness_reason}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Mathematical Temporal Decay Pill */}
                    {finding.decay_factor !== undefined && finding.decay_factor !== null && finding.days_old !== undefined && finding.days_old !== null && (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '10px',
                          fontFamily: 'var(--font-mono)',
                          color: '#A1A1AA',
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid #27272A',
                          borderRadius: '4px',
                          padding: '3px 7px',
                        }}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Clock size={10} color="#71717A" />
                          <span>Decay: e^(-0.05×{finding.days_old.toFixed(1)}d)</span>
                        </span>
                        <span style={{ color: '#06B6D4', fontWeight: 600 }}>
                          ×{finding.decay_factor.toFixed(2)} factor
                        </span>
                      </div>
                    )}

                    {/* Inspect Evidence button — only shown for real DB findings (not live-* SSE ones) */}
                    {onInspectFinding && investigationId && !finding.id.startsWith('live-') && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onInspectFinding(finding) }}
                        style={{
                          alignSelf: 'flex-start',
                          background: 'rgba(99,102,241,0.1)',
                          border: '1px solid rgba(99,102,241,0.28)',
                          borderRadius: '4px',
                          padding: '3px 9px',
                          cursor: 'pointer',
                          color: '#A5B4FC',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '10px',
                          fontWeight: 600,
                          marginTop: '2px',
                          transition: 'background 150ms ease',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(99,102,241,0.2)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(99,102,241,0.1)')}
                      >
                        Inspect Evidence →
                      </button>
                    )}

                    {/* Missing Claims (if any) */}
                    {finding.missing_claims && finding.missing_claims.length > 0 && (
                      <div style={{ fontSize: '11px', color: '#FCA5A5' }}>
                        <span style={{ color: '#71717A', fontFamily: 'var(--font-mono)' }}>Missing Claims: </span>
                        {finding.missing_claims.map((claim) => (
                          <span
                            key={claim}
                            style={{
                              background: 'rgba(239, 68, 68, 0.15)',
                              padding: '1px 4px',
                              borderRadius: '3px',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '10px',
                              marginRight: '4px',
                            }}
                          >
                            {claim}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Reasons / Audit Justification */}
                    {finding.reasons && finding.reasons.length > 0 && (
                      <div style={{ fontSize: '11px', color: '#A1A1AA', lineHeight: 1.35 }}>
                        {finding.reasons[0]}
                      </div>
                    )}

                    {/* Correlated Mitigation (if present) */}
                    {finding.recommended_mitigation_id && (
                      <div
                        style={{
                          background: 'rgba(99, 102, 241, 0.1)',
                          border: '1px solid rgba(99, 102, 241, 0.25)',
                          borderRadius: '6px',
                          padding: '6px 8px',
                          fontSize: '11px',
                          color: '#C7D2FE',
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>Playbook Mitigation: </span>
                        <span>{finding.recommended_mitigation_id}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Red Herrings Filtered Section (Stage 3 Adversarial Filter) */}
            {redHerrings.length > 0 && (
              <div
                style={{
                  marginTop: '8px',
                  background: '#0D0D0F',
                  border: '1px dashed #3F3F46',
                  borderRadius: '8px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FilterX size={14} color="#A1A1AA" />
                  <span style={{ fontSize: '11px', fontWeight: 600, color: '#A1A1AA', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
                    Stage 3 Adversarial Red-Herrings Rejected
                  </span>
                </div>
                {redHerrings.map((rh) => (
                  <div key={rh.incident_id} style={{ fontSize: '11px', color: '#71717A', lineHeight: 1.35 }}>
                    <span style={{ color: '#F87171', fontWeight: 600 }}>[{rh.incident_id}] </span>
                    <span style={{ color: '#D4D4D8' }}>{rh.title}: </span>
                    <span>{rh.rationale}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
