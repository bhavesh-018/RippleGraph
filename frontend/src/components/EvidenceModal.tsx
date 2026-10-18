import { useState, useEffect } from 'react'
import { X, AlertOctagon, Zap, GitBranch, Server, Link2, ShieldCheck, Loader2 } from 'lucide-react'
import type { Finding, EvidenceResult } from '../types'
import { api } from '../api/client'

interface EvidenceModalProps {
  finding: Finding
  investigationId: string
  onClose: () => void
}

function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase()
  const isBreaking = s === 'incompatible'
  const isPotential = s.includes('potential')
  const bg = isBreaking
    ? 'rgba(239,68,68,0.2)'
    : isPotential ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)'
  const color = isBreaking ? '#FCA5A5' : isPotential ? '#FCD34D' : '#6EE7B7'
  const label = isBreaking ? 'BREAKING' : isPotential ? 'POTENTIAL RISK' : 'COMPATIBLE'
  return (
    <span style={{
      fontSize: '9px', fontWeight: 700, fontFamily: 'var(--font-mono)',
      background: bg, color, padding: '2px 6px', borderRadius: '4px', letterSpacing: '0.04em',
    }}>
      {label}
    </span>
  )
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#71717A' }}>
        {icon}
        <span style={{
          fontSize: '10px', fontWeight: 600, textTransform: 'uppercase',
          letterSpacing: '0.08em', fontFamily: 'var(--font-mono)',
        }}>
          {title}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {children}
      </div>
    </div>
  )
}

export default function EvidenceModal({ finding, investigationId, onClose }: EvidenceModalProps) {
  const [evidence, setEvidence] = useState<EvidenceResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.getFindingEvidence(investigationId, finding.id)
      .then(setEvidence)
      .catch(e => setError(e.message || 'Failed to load evidence'))
      .finally(() => setLoading(false))
  }, [finding.id, investigationId])

  return (
    // Dark overlay — click outside to close
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backdropFilter: 'blur(4px)',
      }}
    >
      {/* Modal box */}
      <div
        onClick={e => e.stopPropagation()}
        className="evidence-modal-box"
        style={{
          background: '#111113',
          border: '1px solid #27272A',
          borderRadius: '12px',
          width: '640px',
          maxWidth: '95vw',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0,0,0,0.8)',
        }}
      >
        {/* Modal Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid #1F1F23', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <GitBranch size={15} color="#71717A" />
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#F4F4F5' }}>
              Evidence Path Inspector
            </span>
            <StatusBadge status={finding.status} />
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#52525B', padding: '4px', borderRadius: '4px',
              display: 'flex', alignItems: 'center',
              transition: 'color 150ms ease',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#A1A1AA')}
            onMouseLeave={e => (e.currentTarget.style.color = '#52525B')}
          >
            <X size={16} />
          </button>
        </div>

        {/* Service strip */}
        <div style={{
          padding: '12px 20px', background: '#0D0D0F',
          borderBottom: '1px solid #1F1F23', flexShrink: 0,
        }}>
          <span style={{ fontSize: '15px', fontWeight: 700, color: '#F4F4F5', letterSpacing: '-0.01em' }}>
            {finding.service_name || finding.service_id}
          </span>
          <span style={{ marginLeft: '10px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#52525B' }}>
            Hop {finding.hop_depth ?? 0} · {finding.category}
          </span>
        </div>

        {/* Scrollable body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '22px' }}>

          {loading && (
            <div style={{ textAlign: 'center', color: '#71717A', fontSize: '12px', padding: '48px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <Loader2 size={20} className="animate-spin" color="#71717A" />
              <span>Loading evidence from graph…</span>
            </div>
          )}

          {error && (
            <div style={{
              background: 'rgba(239,68,68,0.1)', border: '1px solid #7F1D1D',
              borderRadius: '8px', padding: '12px', color: '#FCA5A5', fontSize: '12px',
            }}>
              {error}
            </div>
          )}

          {evidence && (
            <>
              {/* Audit Reasons */}
              {evidence.finding.reasons.length > 0 && (
                <Section icon={<AlertOctagon size={13} />} title="Audit Justification">
                  {evidence.finding.reasons.map((r, i) => (
                    <div key={i} style={{
                      fontSize: '12px', color: '#A1A1AA', lineHeight: 1.55,
                      paddingLeft: '10px', borderLeft: '2px solid #27272A',
                    }}>
                      {r}
                    </div>
                  ))}
                </Section>
              )}

              {/* Missing Claims */}
              {evidence.finding.missing_claims.length > 0 && (
                <Section icon={<Zap size={13} />} title="Missing Claims (Breaking)">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {evidence.finding.missing_claims.map(c => (
                      <span key={c} style={{
                        background: 'rgba(239,68,68,0.12)',
                        color: '#FCA5A5',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        border: '1px solid rgba(239,68,68,0.2)',
                      }}>
                        {c}
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Dependency Chains */}
              {evidence.finding.dependency_chains.length > 0 && (
                <Section icon={<GitBranch size={13} />} title="Dependency Chain">
                  {evidence.finding.dependency_chains.map((chain, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: '6px',
                      flexWrap: 'wrap', fontSize: '11px',
                      fontFamily: 'var(--font-mono)', color: '#A1A1AA',
                    }}>
                      {chain.map((node, j) => (
                        <span key={j} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{
                            background: '#1C1C1F',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            color: j === 0 ? '#FCD34D' : '#F4F4F5',
                            border: '1px solid #27272A',
                          }}>
                            {node}
                          </span>
                          {j < chain.length - 1 && (
                            <span style={{ color: '#3F3F46' }}>→</span>
                          )}
                        </span>
                      ))}
                    </div>
                  ))}
                </Section>
              )}

              {/* Affected Service */}
              {evidence.service && (
                <Section icon={<Server size={13} />} title="Affected Service">
                  <div style={{
                    background: '#0D0D0F', border: '1px solid #27272A',
                    borderRadius: '8px', padding: '12px',
                    display: 'flex', flexDirection: 'column', gap: '6px',
                  }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#F4F4F5' }}>
                      {evidence.service.name}
                    </div>
                    <div style={{ fontSize: '11px', color: '#71717A', fontFamily: 'var(--font-mono)' }}>
                      {evidence.service.tier?.toUpperCase()} · {evidence.service.owner_team} · :{evidence.service.port}
                    </div>
                    {evidence.service.description && (
                      <div style={{ fontSize: '11px', color: '#A1A1AA', lineHeight: 1.5 }}>
                        {evidence.service.description}
                      </div>
                    )}
                    {evidence.service.runtime && (
                      <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#3F3F46' }}>
                        {evidence.service.runtime}
                      </div>
                    )}
                  </div>
                </Section>
              )}

              {/* Historical Incidents + Mitigations */}
              {evidence.incidents.length > 0 && (
                <Section
                  icon={<Link2 size={13} />}
                  title={`Historical Evidence (${evidence.incidents.length} incident${evidence.incidents.length > 1 ? 's' : ''})`}
                >
                  {evidence.incidents.map(inc => (
                    <div key={inc.id} style={{
                      background: '#0D0D0F', border: '1px solid #27272A',
                      borderRadius: '8px', padding: '12px',
                      display: 'flex', flexDirection: 'column', gap: '8px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: '#F87171', fontWeight: 700 }}>
                          {inc.id}
                        </span>
                        <span style={{ fontSize: '12px', color: '#D4D4D8', fontWeight: 500, flex: 1 }}>
                          {inc.title}
                        </span>
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: '9px', color: '#71717A',
                          background: '#1C1C1F', padding: '1px 5px', borderRadius: '3px',
                        }}>
                          {inc.severity?.toUpperCase()}
                        </span>
                      </div>
                      {inc.description && (
                        <div style={{ fontSize: '11px', color: '#71717A', lineHeight: 1.45 }}>
                          {inc.description}
                        </div>
                      )}
                      {inc.mitigation && (
                        <div style={{
                          background: 'rgba(99,102,241,0.08)',
                          border: '1px solid rgba(99,102,241,0.22)',
                          borderRadius: '6px', padding: '10px 12px',
                          display: 'flex', flexDirection: 'column', gap: '4px',
                        }}>
                          <div style={{
                            fontSize: '9px', fontWeight: 700, color: '#818CF8',
                            fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
                          }}>
                            ✅ Playbook · {inc.mitigation.id}
                          </div>
                          <div style={{ fontSize: '12px', color: '#C7D2FE', fontWeight: 500 }}>
                            {inc.mitigation.title}
                          </div>
                          <div style={{ fontSize: '11px', color: '#A5B4FC', lineHeight: 1.45 }}>
                            {inc.mitigation.description}
                          </div>
                          <div style={{ fontSize: '10px', color: '#6366F1', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                            Validation: {inc.mitigation.validation_method}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </Section>
              )}

              {/* Recommended Contract */}
              {(evidence.contract || evidence.finding.recommended_contract_id) && (
                <Section icon={<ShieldCheck size={13} />} title="Recommended Migration Contract">
                  <div style={{
                    background: 'rgba(16,185,129,0.07)',
                    border: '1px solid rgba(16,185,129,0.2)',
                    borderRadius: '8px', padding: '10px 14px',
                    display: 'flex', flexDirection: 'column', gap: '4px',
                  }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#6EE7B7', fontWeight: 600 }}>
                      {evidence.contract?.id || evidence.finding.recommended_contract_id}
                    </span>
                    {evidence.contract?.version && (
                      <span style={{ fontSize: '11px', color: '#34D399' }}>v{evidence.contract.version}</span>
                    )}
                    {evidence.contract?.description && (
                      <span style={{ fontSize: '11px', color: '#6EE7B7', lineHeight: 1.45 }}>
                        {evidence.contract.description}
                      </span>
                    )}
                  </div>
                </Section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
