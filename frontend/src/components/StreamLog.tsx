import { useState, useEffect, useRef } from 'react'
import { Terminal, X, ChevronDown, Copy, Check } from 'lucide-react'
import type { LogEntry } from '../api/sse'

interface StreamLogProps {
  logs: LogEntry[]
  isRunning: boolean
  isComplete: boolean
  stage?: string
}

export default function StreamLog({
  logs = [],
  isRunning,
  isComplete,
}: StreamLogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const prevRunning = useRef(isRunning)
  const logEndRef = useRef<HTMLDivElement>(null)

  // Auto-open when rehearsal starts, auto-close when completed
  useEffect(() => {
    if (isRunning && !prevRunning.current) {
      setIsOpen(true)
    } else if (!isRunning && prevRunning.current) {
      setIsOpen(false)
    }
    prevRunning.current = isRunning
  }, [isRunning])

  // Auto-scroll to bottom as new log events stream in
  useEffect(() => {
    if (isOpen) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, isOpen])

  // Type badge color mapping
  const logTypeStyle = (type: string) => {
    switch (type) {
      case 'STAGE':
        return { color: '#818CF8', bg: 'rgba(129, 140, 248, 0.12)', border: 'rgba(129, 140, 248, 0.3)' }
      case 'DISCOVER':
        return { color: '#06B6D4', bg: 'rgba(6, 182, 212, 0.12)', border: 'rgba(6, 182, 212, 0.3)' }
      case 'COMPAT':
        return { color: '#10B981', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.3)' }
      case 'PATH':
        return { color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.3)' }
      case 'MEMORY':
        return { color: '#A78BFA', bg: 'rgba(167, 139, 250, 0.12)', border: 'rgba(167, 139, 250, 0.3)' }
      case 'FINDING':
        return { color: '#FB923C', bg: 'rgba(251, 146, 60, 0.12)', border: 'rgba(251, 146, 60, 0.3)' }
      case 'COMPLETE':
        return { color: '#34D399', bg: 'rgba(52, 211, 153, 0.15)', border: 'rgba(52, 211, 153, 0.4)' }
      case 'ERROR':
        return { color: '#F87171', bg: 'rgba(248, 113, 113, 0.15)', border: 'rgba(248, 113, 113, 0.4)' }
      default:
        return { color: '#A1A1AA', bg: 'rgba(161, 161, 170, 0.1)', border: '#27272A' }
    }
  }

  const handleCopyLogs = () => {
    const text = logs
      .map((l) => `[${l.timestamp}] [${l.type}] ${l.message}`)
      .join('\n')
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  // If no logs yet, keep hidden until first rehearsal
  if (logs.length === 0 && !isRunning) {
    return null
  }

  return (
    <>
      {/* Closed State: Sleek Floating Console Trigger Button */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          title="Click to view live stream logs"
          style={{
            position: 'absolute',
            bottom: '16px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 20,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '7px 14px',
            background: 'rgba(18, 18, 22, 0.92)',
            backdropFilter: 'blur(10px)',
            border: '1px solid #27272A',
            borderRadius: '20px',
            color: '#EDEDED',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
            boxShadow: '0 6px 20px rgba(0, 0, 0, 0.5)',
            transition: 'all 150ms ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#3F3F46'
            e.currentTarget.style.background = 'rgba(28, 28, 34, 0.96)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#27272A'
            e.currentTarget.style.background = 'rgba(18, 18, 22, 0.92)'
          }}
        >
          <Terminal size={14} color="#06B6D4" />
          <span style={{ fontWeight: 500 }}>Stream Log</span>
          <span
            style={{
              fontSize: '10.5px',
              background: '#27272A',
              color: '#A1A1AA',
              padding: '1px 6px',
              borderRadius: '10px',
            }}
          >
            {logs.length} {logs.length === 1 ? 'event' : 'events'}
          </span>
          {isRunning ? (
            <span
              className="pulse-dot"
              style={{ background: '#06B6D4', width: '7px', height: '7px' }}
            />
          ) : isComplete ? (
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#10B981',
              }}
            />
          ) : null}
        </button>
      )}

      {/* Open State: Spacious, Highly Readable Stream Console Window */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            bottom: '16px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 25,
            width: 'min(860px, calc(100% - 32px))',
            height: '280px',
            display: 'flex',
            flexDirection: 'column',
            background: 'rgba(10, 10, 13, 0.96)',
            backdropFilter: 'blur(16px)',
            border: '1px solid #27272A',
            borderRadius: '10px',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)',
            overflow: 'hidden',
            animation: 'log-pop 180ms ease-out',
          }}
        >
          {/* Console Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 14px',
              borderBottom: '1px solid #1F1F24',
              background: '#121216',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={14} color="#06B6D4" />
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  letterSpacing: '0.06em',
                  color: '#EDEDED',
                  textTransform: 'uppercase',
                }}
              >
                Stream Console
              </span>
              <span
                style={{
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  color: '#71717A',
                  background: '#1C1C21',
                  border: '1px solid #27272A',
                  padding: '1px 6px',
                  borderRadius: '4px',
                }}
              >
                {logs.length} events
              </span>
              {isRunning && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginLeft: '6px' }}>
                  <span className="pulse-dot" style={{ background: '#06B6D4', width: '6px', height: '6px' }} />
                  <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#06B6D4' }}>
                    Streaming...
                  </span>
                </div>
              )}
              {isComplete && !isRunning && (
                <span
                  style={{
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    color: '#34D399',
                    background: 'rgba(52, 211, 153, 0.1)',
                    border: '1px solid rgba(52, 211, 153, 0.3)',
                    padding: '1px 6px',
                    borderRadius: '4px',
                  }}
                >
                  Completed
                </span>
              )}
            </div>

            {/* Header Actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                onClick={handleCopyLogs}
                title="Copy all logs to clipboard"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: '#18181C',
                  border: '1px solid #27272A',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  color: copied ? '#34D399' : '#A1A1AA',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  transition: 'all 120ms ease',
                }}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close Stream Console"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#18181C',
                  border: '1px solid #27272A',
                  borderRadius: '4px',
                  padding: '4px',
                  color: '#A1A1AA',
                  cursor: 'pointer',
                  transition: 'all 120ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#EDEDED'
                  e.currentTarget.style.borderColor = '#3F3F46'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#A1A1AA'
                  e.currentTarget.style.borderColor = '#27272A'
                }}
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* Console Log Feed */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '8px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
              scrollbarWidth: 'thin',
              scrollbarColor: '#27272A #0A0A0D',
            }}
          >
            {logs.map((entry) => {
              const typeStyle = logTypeStyle(entry.type)
              return (
                <div
                  key={entry.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    lineHeight: 1.55,
                    transition: 'background 100ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent'
                  }}
                >
                  {/* Timestamp */}
                  <span
                    style={{
                      color: '#52525B',
                      fontSize: '11px',
                      flexShrink: 0,
                      minWidth: '65px',
                    }}
                  >
                    {entry.timestamp}
                  </span>

                  {/* Type Badge */}
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      letterSpacing: '0.04em',
                      color: typeStyle.color,
                      background: typeStyle.bg,
                      border: `1px solid ${typeStyle.border}`,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      flexShrink: 0,
                      minWidth: '64px',
                      textAlign: 'center',
                    }}
                  >
                    {entry.type}
                  </span>

                  {/* Message */}
                  <span
                    style={{
                      color: '#E4E4E7',
                      wordBreak: 'break-word',
                      flex: 1,
                    }}
                  >
                    {entry.message}
                  </span>
                </div>
              )
            })}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </>
  )
}
