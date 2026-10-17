import { useState, useRef } from 'react'
import {
  Sparkles,
  Search,
  Code,
  Copy,
  Check,
  X,
  Loader2,
  ChevronDown,
  ChevronUp,
  Database,
} from 'lucide-react'
import { api } from '../api/client'
import type { NLQueryResult } from '../types'

interface NLQueryBarProps {
  onHighlightServices: (serviceIds: string[]) => void
  selectedChangeId?: string
}

const PRESET_QUERIES = [
  'What breaks if auth-service fails?',
  'Services depending on auth-service',
  'Platform tier services',
  'Incidents affecting payment-service',
]

// Known services in the 10-node RippleGraph topology
const ALL_SERVICE_IDS = [
  'auth-service',
  'payment-service',
  'api-gateway',
  'order-service',
  'user-service',
  'billing-service',
  'notification-service',
  'inventory-service',
  'analytics-service',
  'audit-service',
]

export default function NLQueryBar({
  onHighlightServices,
  selectedChangeId,
}: NLQueryBarProps) {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<NLQueryResult | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleQuery = async (queryText?: string) => {
    const q = (queryText ?? question).trim()
    if (!q || q.length < 5) return

    setLoading(true)
    setError(null)
    if (queryText) setQuestion(queryText)

    try {
      const res = await api.queryNaturalLanguage(q, selectedChangeId)
      setResult(res)
      setExpanded(true)

      // Extract matching service IDs from records to highlight in the graph
      const matched = new Set<string>()
      const recordsJson = JSON.stringify(res.records).toLowerCase()

      ALL_SERVICE_IDS.forEach((id) => {
        if (recordsJson.includes(id.toLowerCase())) {
          matched.add(id)
        }
      })

      // Also check question text (e.g., if asking about auth-service)
      ALL_SERVICE_IDS.forEach((id) => {
        if (q.toLowerCase().includes(id.toLowerCase())) {
          matched.add(id)
        }
      })

      onHighlightServices(Array.from(matched))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setQuestion('')
    setResult(null)
    setError(null)
    setExpanded(false)
    onHighlightServices([])
    if (inputRef.current) inputRef.current.focus()
  }

  const handleCopyCypher = () => {
    if (!result?.cypher) return
    navigator.clipboard.writeText(result.cypher)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: '16px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 20,
        width: '92%',
        maxWidth: '740px',
      }}
    >
      {/* Main Command Bar Container */}
      <div
        style={{
          background: 'rgba(17, 17, 20, 0.94)',
          backdropFilter: 'blur(16px)',
          border: error ? '1px solid #EF4444' : result ? '1px solid #06B6D4' : '1px solid #27272A',
          borderRadius: expanded && result ? '12px 12px 0 0' : '12px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.05)',
          padding: '10px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          transition: 'all 200ms ease',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '26px',
              height: '26px',
              borderRadius: '6px',
              background: 'rgba(6, 182, 212, 0.15)',
              color: '#06B6D4',
              flexShrink: 0,
            }}
          >
            <Sparkles size={15} />
          </div>

          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleQuery()
              if (e.key === 'Escape') handleClear()
            }}
            placeholder='Ask about the service graph (e.g. "What breaks if auth-service fails?")...'
            disabled={loading}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#F4F4F5',
              fontSize: '13px',
              fontFamily: 'inherit',
            }}
          />

          {question && (
            <button
              onClick={handleClear}
              title="Clear query"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#71717A',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <X size={14} />
            </button>
          )}

          <button
            onClick={() => handleQuery()}
            disabled={loading || question.trim().length < 5}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              background: question.trim().length >= 5 ? '#06B6D4' : '#27272A',
              color: question.trim().length >= 5 ? '#000000' : '#71717A',
              fontSize: '12px',
              fontWeight: 600,
              cursor: question.trim().length >= 5 ? 'pointer' : 'not-allowed',
              transition: 'background 150ms ease',
            }}
          >
            {loading ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                <span>Generating Cypher...</span>
              </>
            ) : (
              <>
                <Search size={13} />
                <span>Ask Graph</span>
              </>
            )}
          </button>
        </div>

        {/* Quick query presets */}
        {!result && !error && (
          <div
            className="hide-scrollbar"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              overflowX: 'auto',
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
              paddingTop: '2px',
            }}
          >
            
            {PRESET_QUERIES.map((pq, idx) => (
              <button
                key={idx}
                onClick={() => handleQuery(pq)}
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid #27272A',
                  borderRadius: '12px',
                  padding: '3px 9px',
                  fontSize: '11px',
                  color: '#A1A1AA',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 120ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#06B6D4'
                  e.currentTarget.style.color = '#FFFFFF'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#27272A'
                  e.currentTarget.style.color = '#A1A1AA'
                }}
              >
                {pq}
              </button>
            ))}
          </div>
        )}

        {/* Error message */}
        {error && (
          <div
            style={{
              padding: '6px 10px',
              borderRadius: '6px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#FCA5A5',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              style={{ background: 'transparent', border: 'none', color: '#FCA5A5', cursor: 'pointer' }}
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Expandable Result & Cypher Card */}
      {result && (
        <div
          style={{
            background: 'rgba(13, 13, 16, 0.98)',
            backdropFilter: 'blur(16px)',
            border: '1px solid #06B6D4',
            borderTop: 'none',
            borderRadius: '0 0 12px 12px',
            padding: '12px 14px',
            boxShadow: '0 16px 40px rgba(0, 0, 0, 0.8)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          {/* Result Header Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: 'rgba(6, 182, 212, 0.15)',
                  color: '#06B6D4',
                  fontSize: '11px',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <Database size={11} />
                <span>FalkorDB Executed</span>
              </div>
              <span style={{ fontSize: '12px', color: '#A1A1AA' }}>
                {result.total} record{result.total === 1 ? '' : 's'} returned • matching nodes highlighted in graph
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={() => setExpanded(!expanded)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'transparent',
                  border: '1px solid #27272A',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  color: '#A1A1AA',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                {expanded ? (
                  <>
                    <span>Hide Details</span>
                    <ChevronUp size={12} />
                  </>
                ) : (
                  <>
                    <span>Show Details</span>
                    <ChevronDown size={12} />
                  </>
                )}
              </button>

              <button
                onClick={handleClear}
                style={{
                  background: 'transparent',
                  border: '1px solid #27272A',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  color: '#71717A',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                Reset
              </button>
            </div>
          </div>

          {/* Details Drawer */}
          {expanded && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '4px' }}>
              {/* Generated Cypher Code Block */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '4px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: '#71717A' }}>
                    <Code size={12} />
                    <span>Generated Cypher (Read-Only Guard Passed):</span>
                  </div>
                  <button
                    onClick={handleCopyCypher}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'transparent',
                      border: 'none',
                      color: copied ? '#10B981' : '#71717A',
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    {copied ? <Check size={11} /> : <Copy size={11} />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <pre
                  style={{
                    background: '#09090B',
                    border: '1px solid #27272A',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    color: '#67E8F9',
                    margin: 0,
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {result.cypher}
                </pre>
              </div>

              {/* Records Table Preview */}
              {result.records.length > 0 && (
                <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <thead>
                      <tr style={{ borderBottom: '1px solid #27272A', background: '#141417' }}>
                        {result.columns.map((col, idx) => (
                          <th
                            key={idx}
                            style={{
                              padding: '6px 8px',
                              textAlign: 'left',
                              color: '#71717A',
                              fontWeight: 600,
                            }}
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.records.slice(0, 10).map((row, rIdx) => (
                        <tr
                          key={rIdx}
                          style={{
                            borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                          }}
                        >
                          {result.columns.map((col, cIdx) => {
                            const val = row[col]
                            const display =
                              val === null || val === undefined
                                ? 'null'
                                : typeof val === 'object'
                                ? JSON.stringify(val)
                                : String(val)
                            return (
                              <td
                                key={cIdx}
                                style={{
                                  padding: '5px 8px',
                                  color: '#E4E4E7',
                                  maxWidth: '220px',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {display}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {result.records.length > 10 && (
                    <div style={{ textAlign: 'center', fontSize: '10px', color: '#71717A', padding: '4px' }}>
                      Showing first 10 of {result.total} records
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
