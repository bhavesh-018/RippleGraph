import { useState, useEffect } from 'react'
import React from 'react'
import {
  X,
  BrainCircuit,
  TrendingUp,
  ArrowDown,
  RotateCcw,
  Zap,
} from 'lucide-react'
import type { MemoryComparisonResponse } from '../types'
import { api } from '../api/client'

/* ── Shared style constants ────────────────────────────── */
const statCard: React.CSSProperties = {
  background: '#0D0D10',
  border: '1px solid #1F1F24',
  borderRadius: '6px',
  padding: '8px 10px',
}
const statLabel: React.CSSProperties = {
  fontSize: '9px',
  fontFamily: 'var(--font-mono)',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.04em',
  display: 'block',
  marginBottom: '2px',
}
const statValue: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: 700,
  lineHeight: 1.1,
}
const statSub: React.CSSProperties = {
  fontSize: '9px',
  color: '#3F3F46',
  fontFamily: 'var(--font-mono)',
  marginTop: '2px',
  display: 'block',
}
const compareCard: React.CSSProperties = {
  background: '#0D0D10',
  border: '1px solid #1E1E24',
  borderRadius: '6px',
  padding: '8px 10px',
}
const barTrack: React.CSSProperties = {
  width: '100%',
  height: '4px',
  background: '#27272A',
  borderRadius: '2px',
  overflow: 'hidden',
}
const barFill: React.CSSProperties = {
  height: '100%',
  borderRadius: '2px',
  transition: 'width 500ms ease',
}

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
        padding: '12px',
        animation: 'log-pop 180ms ease-out',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="memory-diff-modal-box"
        style={{
          background: '#0F0F12',
          border: '1px solid #27272A',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '780px',
          maxHeight: 'calc(100dvh - 24px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.85)',
        }}
      >
        {/* ── Header ── */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            padding: '12px 14px',
            borderBottom: '1px solid #1F1F24',
            background: '#131317',
            flexShrink: 0,
            gap: '10px',
          }}
        >
          {/* Left: icon + title */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', minWidth: 0 }}>
            <div
              style={{
                flexShrink: 0,
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
            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#EDEDED', lineHeight: 1.3 }}>
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
                    flexShrink: 0,
                  }}
                >
                  {changeId}
                </span>
              </div>
              <p style={{ fontSize: '10px', color: '#52525B', margin: '2px 0 0', lineHeight: 1.4 }}>
                Cold Start (Memory OFF) vs FalkorDB Graph Memory (Memory ON)
              </p>
            </div>
          </div>

          {/* Right: actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            <button
              type="button"
              onClick={loadComparison}
              disabled={loading}
              title={loading ? 'Comparing...' : 'Re-run comparison'}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: '#1C1C21',
                border: '1px solid #27272A',
                borderRadius: '4px',
                padding: '5px 8px',
                color: '#A1A1AA',
                fontSize: '11px',
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              <RotateCcw size={12} className={loading ? 'spin' : ''} />
              <span>{loading ? 'Running...' : 'Refresh'}</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              style={{
                background: '#1C1C21',
                border: '1px solid #27272A',
                borderRadius: '4px',
                padding: '5px',
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

        {/* ── Body ── */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
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
              {/* ── Scoreboard: 2×2 grid (fits all screen sizes) ── */}
              <div
                style={{
                  background: 'linear-gradient(180deg, #16161B 0%, #111115 100%)',
                  border: '1px solid #27272A',
                  borderRadius: '10px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                  {/* Cold Start */}
                  <div style={statCard}>
                    <span style={{ ...statLabel, color: '#71717A' }}>Cold Start</span>
                    <div style={{ ...statValue, color: '#A1A1AA' }}>
                      {Math.round(data.summary.avg_confidence_without_memory * 100)}%
                    </div>
                    <span style={statSub}>Memory OFF</span>
                  </div>

                  {/* FalkorDB */}
                  <div style={statCard}>
                    <span style={{ ...statLabel, color: '#E4E4E7' }}>FalkorDB</span>
                    <div style={{ ...statValue, color: '#FFFFFF' }}>
                      {Math.round(data.summary.avg_confidence_with_memory * 100)}%
                    </div>
                    <span style={statSub}>Memory ON</span>
                  </div>

                  {/* Confidence Boost */}
                  <div style={statCard}>
                    <span style={{ ...statLabel, color: '#10B981' }}>Boost</span>
                    <div style={{ ...statValue, color: '#34D399', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <TrendingUp size={14} />
                      <span>+{data.summary.overall_confidence_gain_pct}%</span>
                    </div>
                    <span style={statSub}>Confidence gain</span>
                  </div>

                  {/* Reaffirmed */}
                  <div style={statCard}>
                    <span style={{ ...statLabel, color: '#3B82F6' }}>Reaffirmed</span>
                    <div style={{ ...statValue, color: '#93C5FD' }}>
                      {data.summary.reaffirmed_count}/{data.summary.total_services_analyzed}
                    </div>
                    <span style={statSub}>Services</span>
                  </div>
                </div>

                {/* Verdict Text */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    background: '#16161A',
                    border: '1px solid #27272A',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '11.5px',
                    color: '#D4D4D8',
                    lineHeight: 1.45,
                  }}
                >
                  <BrainCircuit size={14} color="#A1A1AA" style={{ flexShrink: 0, marginTop: '2px' }} />
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
                        {/* Service header row — wraps naturally on narrow screens */}
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '6px', flexWrap: 'wrap' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#EDEDED' }}>
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
                                whiteSpace: 'nowrap',
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
                                gap: '3px',
                                fontSize: '9px',
                                fontFamily: 'var(--font-mono)',
                                fontWeight: 600,
                                background: 'rgba(16, 185, 129, 0.15)',
                                color: '#6EE7B7',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                padding: '2px 6px',
                                borderRadius: '12px',
                                whiteSpace: 'nowrap',
                                flexShrink: 0,
                              }}
                            >
                              <Zap size={9} />
                              Reaffirmed (+{deltaGain}%)
                            </span>
                          )}
                        </div>

                        {/* Comparison: stacked column — works on any screen width */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {/* Cold Start */}
                          <div style={compareCard}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#71717A', marginBottom: '4px' }}>
                              <span>Cold Start:</span>
                              <span style={{ color: '#A1A1AA', fontWeight: 600 }}>{confWithoutPct}%</span>
                            </div>
                            <div style={barTrack}>
                              <div style={{ ...barFill, width: `${confWithoutPct}%`, background: '#52525B' }} />
                            </div>
                            <div style={{ fontSize: '10px', color: '#52525B', marginTop: '3px' }}>
                              Isolated reasoning without history
                            </div>
                          </div>

                          {/* Divider arrow */}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3F3F46' }}>
                            <ArrowDown size={12} />
                          </div>

                          {/* FalkorDB Memory */}
                          <div style={{ ...compareCard, border: '1px solid rgba(167, 139, 250, 0.2)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#A78BFA', marginBottom: '4px' }}>
                              <span>With Temporal Memory:</span>
                              <span style={{ color: '#34D399', fontWeight: 700 }}>{confWithPct}%</span>
                            </div>
                            <div style={barTrack}>
                              <div style={{ ...barFill, width: `${confWithPct}%`, background: '#34D399' }} />
                            </div>
                            <div style={{ fontSize: '10px', color: '#34D399', marginTop: '3px' }}>
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
