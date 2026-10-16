import { useState, useEffect } from 'react'
import {
  X,
  BrainCircuit,
  TrendingUp,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  Layers,
  RotateCcw,
} from 'lucide-react'
import type { MemoryComparisonResponse } from '../types'
import { api } from '../api/client'

interface MemoryDiffModalProps {
  changeId: string
  onClose: () => void
}

export default function MemoryDiffModal({ changeId, onClose }: MemoryDiffModalProps) {
  const [data, setData] = useState<MemoryComparisonResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadComparison = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await api.compareMemory(changeId)
      setData(res)
    } catch (err: unknown) {
      console.error('Failed to load memory comparison:', err)
      setError(err instanceof Error ? err.message : 'Failed to execute memory comparison')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadComparison()
  }, [changeId])

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(0, 0, 0, 0.78)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'log-pop 180ms ease-out',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#0F0F12',
          border: '1px solid #27272A',
          borderRadius: '12px',
          width: '780px',
          maxWidth: '95vw',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.85)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 20px',
            borderBottom: '1px solid #1F1F24',
            background: '#131317',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                background: 'rgba(167, 139, 250, 0.15)',
                border: '1px solid rgba(167, 139, 250, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BrainCircuit size={16} color="#A78BFA" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#EDEDED' }}>
                  Temporal Memory Comparison
                </span>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '10px',
                    background: '#1F1F24',
                    color: '#A1A1AA',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    border: '1px solid #2E2E35',
                  }}
                >
                  {changeId}
                </span>
              </div>
              <p style={{ fontSize: '11px', color: '#71717A', margin: 0 }}>
                Visual diff comparing Cold Start (Memory OFF) vs FalkorDB Graph Memory (Memory ON)
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              onClick={loadComparison}
              disabled={loading}
              title="Re-run dual-mode comparison"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: '#1C1C21',
                border: '1px solid #27272A',
                borderRadius: '4px',
                padding: '4px 8px',
                color: '#A1A1AA',
                fontSize: '11px',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              <RotateCcw size={12} className={loading ? 'spin' : ''} />
              <span>{loading ? 'Comparing...' : 'Refresh'}</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              style={{
                background: '#1C1C21',
                border: '1px solid #27272A',
                borderRadius: '4px',
                padding: '4px',
                color: '#A1A1AA',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            scrollbarWidth: 'thin',
            scrollbarColor: '#27272A #0F0F12',
          }}
        >
          {loading && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#71717A', fontFamily: 'var(--font-mono)' }}>
              <BrainCircuit size={28} color="#A78BFA" style={{ animation: 'spin 2s linear infinite', margin: '0 auto 12px' }} />
              <div>Running dual Change Rehearsals (Cold Start vs FalkorDB)...</div>
            </div>
          )}

          {error && (
            <div
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid #7F1D1D',
                borderRadius: '8px',
                padding: '14px',
                color: '#FCA5A5',
                fontSize: '12px',
              }}
            >
              {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Scoreboard / Verdict Summary */}
              <div
                style={{
                  background: 'linear-gradient(180deg, #16161B 0%, #111115 100%)',
                  border: '1px solid #27272A',
                  borderRadius: '10px',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                  {/* Cold Start Avg */}
                  <div style={{ background: '#0D0D10', border: '1px solid #1F1F24', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#71717A', textTransform: 'uppercase' }}>
                      Cold Start (Off)
                    </span>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#A1A1AA', marginTop: '2px' }}>
                      {Math.round(data.summary.avg_confidence_without_memory * 100)}%
                    </div>
                  </div>

                  {/* FalkorDB Avg */}
                  <div style={{ background: '#0D0D10', border: '1px solid #1F1F24', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#A78BFA', textTransform: 'uppercase' }}>
                      FalkorDB Memory (On)
                    </span>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#C4B5FD', marginTop: '2px' }}>
                      {Math.round(data.summary.avg_confidence_with_memory * 100)}%
                    </div>
                  </div>

                  {/* Confidence Gain */}
                  <div style={{ background: '#0D0D10', border: '1px solid #1F1F24', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#10B981', textTransform: 'uppercase' }}>
                      Confidence Boost
                    </span>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#34D399', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <TrendingUp size={16} />
                      <span>+{data.summary.overall_confidence_gain_pct}%</span>
                    </div>
                  </div>

                  {/* Reaffirmed Count */}
                  <div style={{ background: '#0D0D10', border: '1px solid #1F1F24', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#06B6D4', textTransform: 'uppercase' }}>
                      Reaffirmed Failures
                    </span>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#67E8F9', marginTop: '2px' }}>
                      {data.summary.reaffirmed_count} / {data.summary.total_services_analyzed}
                    </div>
                  </div>
                </div>

                {/* Verdict Text */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    background: 'rgba(167, 139, 250, 0.08)',
                    border: '1px solid rgba(167, 139, 250, 0.22)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '11.5px',
                    color: '#DDD6FE',
                    lineHeight: 1.45,
                  }}
                >
                  <Sparkles size={14} color="#A78BFA" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>{data.summary.memory_verdict}</div>
                </div>
              </div>

              {/* Service By Service Visual Diff */}
              <div>
                <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
                  Per-Service Confidence & Reasoning Deltas
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {data.deltas.map((d) => {
                    const isBreaking = d.status_with_memory.toLowerCase() === 'incompatible'
                    const confWithPct = Math.round(d.confidence_with_memory * 100)
                    const confWithoutPct = Math.round(d.confidence_without_memory * 100)
                    const deltaGain = Math.round(d.confidence_gain_pct)

                    return (
                      <div
                        key={d.service_id}
                        style={{
                          background: '#131317',
                          border: `1px solid ${d.memory_reaffirmed ? 'rgba(167, 139, 250, 0.35)' : '#27272A'}`,
                          borderRadius: '8px',
                          padding: '12px 14px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                          transition: 'border-color 150ms ease',
                        }}
                      >
                        {/* Service Header */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: '#EDEDED' }}>
                              {d.service_name}
                            </span>
                            <span
                              style={{
                                fontSize: '9px',
                                fontFamily: 'var(--font-mono)',
                                fontWeight: 700,
                                background: isBreaking ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                                color: isBreaking ? '#FCA5A5' : '#FCD34D',
                                border: `1px solid ${isBreaking ? '#EF4444' : '#F59E0B'}`,
                                padding: '1px 5px',
                                borderRadius: '3px',
                              }}
                            >
                              {d.status_with_memory.toUpperCase()}
                            </span>
                          </div>

                          {d.memory_reaffirmed && (
                            <span
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '10px',
                                fontFamily: 'var(--font-mono)',
                                fontWeight: 600,
                                background: 'rgba(16, 185, 129, 0.15)',
                                color: '#6EE7B7',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                padding: '2px 7px',
                                borderRadius: '12px',
                              }}
                            >
                              <span>⚡ Reaffirmed from Memory</span>
                              <span>(+{deltaGain}%)</span>
                            </span>
                          )}
                        </div>

                        {/* Side by Side Comparison Row */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '12px', alignItems: 'center' }}>
                          {/* Left: Cold Start */}
                          <div style={{ background: '#0D0D10', border: '1px solid #1E1E24', borderRadius: '6px', padding: '8px 10px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#71717A', marginBottom: '3px' }}>
                              <span>Cold Start:</span>
                              <span style={{ color: '#A1A1AA', fontWeight: 600 }}>{confWithoutPct}%</span>
                            </div>
                            <div style={{ width: '100%', height: '4px', background: '#27272A', borderRadius: '2px', overflow: 'hidden' }}>
                              <div style={{ width: `${confWithoutPct}%`, height: '100%', background: '#71717A', borderRadius: '2px' }} />
                            </div>
                            <div style={{ fontSize: '10px', color: '#52525B', marginTop: '4px' }}>
                              Isolated reasoning without history
                            </div>
                          </div>

                          {/* Center Arrow */}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3F3F46' }}>
                            <ArrowRight size={14} />
                          </div>

                          {/* Right: FalkorDB Memory */}
                          <div style={{ background: '#0D0D10', border: '1px solid #1E1E24', borderRadius: '6px', padding: '8px 10px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#A78BFA', marginBottom: '3px' }}>
                              <span>With Temporal Memory:</span>
                              <span style={{ color: '#34D399', fontWeight: 700 }}>{confWithPct}%</span>
                            </div>
                            <div style={{ width: '100%', height: '4px', background: '#27272A', borderRadius: '2px', overflow: 'hidden' }}>
                              <div style={{ width: `${confWithPct}%`, height: '100%', background: '#34D399', borderRadius: '2px' }} />
                            </div>
                            <div style={{ fontSize: '10px', color: '#34D399', marginTop: '4px' }}>
                              +{deltaGain}% boost via temporal decay e^(-0.05*dt)
                            </div>
                          </div>
                        </div>

                        {/* Memory Explanation text */}
                        {d.memory_explanation && (
                          <div
                            style={{
                              fontSize: '11px',
                              fontFamily: 'var(--font-mono)',
                              color: '#A1A1AA',
                              background: '#0D0D10',
                              borderLeft: '2px solid #8B5CF6',
                              padding: '5px 8px',
                              borderRadius: '0 4px 4px 0',
                              lineHeight: 1.4,
                            }}
                          >
                            {d.memory_explanation}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
