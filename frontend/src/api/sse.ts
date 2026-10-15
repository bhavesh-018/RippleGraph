import { useEffect, useRef, useCallback, useState } from 'react'
import type {
  NodeStatus,
  StageChangedPayload,
  ConsumersFoundPayload,
  CompatibilityCheckedPayload,
  DownstreamPathPayload,
  MemoryRecalledPayload,
  FindingProducedPayload,
  CompletePayload,
} from '../types'

// ── Node state map updated by SSE events ──────────────────────────
export interface NodeStateMap {
  [serviceId: string]: {
    status: NodeStatus
    reason?: string
  }
}

// ── SSE Log Entry ─────────────────────────────────────────────────
export interface LogEntry {
  id: string
  timestamp: string
  type: string
  message: string
}

// ── Stream summary produced by the COMPLETE event ─────────────────
export interface StreamSummary {
  investigation_id: string
  change_id: string
  summary: {
    incompatible: number
    potential_downstream: number
    compatible: number
    unaffected: number
  }
  recommended_contract?: string
  execution_time_ms: number
}

// ── Hook options ──────────────────────────────────────────────────
export interface StreamOptions {
  changeId?: string
  memoryEnabled?: boolean
  disconnectGraph?: boolean
  paceDelayS?: number
}

// ── Hook Return ──────────────────────────────────────────────────
export interface UseInvestigationStreamReturn {
  nodeStates: NodeStateMap
  logs: LogEntry[]
  stage: string
  isRunning: boolean
  isComplete: boolean
  streamSummary: StreamSummary | undefined
  startStream: (opts?: StreamOptions) => void
  stopStream: () => void
}

const BACKEND = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

let logCounter = 0

function makeLogId() {
  return `log-${++logCounter}`
}

function nowTime() {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}

// Map backend status strings → NodeStatus enum values used by the canvas
function toNodeStatus(backendStatus: string): NodeStatus {
  const map: Record<string, NodeStatus> = {
    INCOMPATIBLE: 'INCOMPATIBLE',
    COMPATIBLE: 'COMPATIBLE',
    incompatible: 'INCOMPATIBLE',
    compatible: 'COMPATIBLE',
    potential_downstream: 'POTENTIAL_DOWNSTREAM',
    POTENTIAL_DOWNSTREAM: 'POTENTIAL_DOWNSTREAM',
    unaffected: 'UNAFFECTED',
    UNAFFECTED: 'UNAFFECTED',
  }
  return map[backendStatus] ?? 'EVALUATING'
}

export function useInvestigationStream(): UseInvestigationStreamReturn {
  const [nodeStates, setNodeStates] = useState<NodeStateMap>({})
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [stage, setStage] = useState<string>('')
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [streamSummary, setStreamSummary] = useState<StreamSummary | undefined>(undefined)
  const eventSourceRef = useRef<EventSource | null>(null)

  const addLog = useCallback((type: string, message: string) => {
    setLogs(prev => [
      ...prev,
      { id: makeLogId(), timestamp: nowTime(), type, message },
    ])
  }, [])

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsRunning(false)
  }, [])

  const startStream = useCallback((opts: StreamOptions = {}) => {
    const {
      changeId = 'CHG-001',
      memoryEnabled = true,
      disconnectGraph = false,
      paceDelayS = 0.35,
    } = opts

    // Reset
    stopStream()
    setNodeStates({})
    setLogs([])
    setStage('')
    setIsComplete(false)
    setStreamSummary(undefined)
    setIsRunning(true)

    addLog('SYSTEM', `Starting stream for ${changeId}`)

    const params = new URLSearchParams({
      change_id: changeId,
      memory_enabled: String(memoryEnabled),
      disconnect_graph: String(disconnectGraph),
      pace_delay_s: String(paceDelayS),
    })

    const url = `${BACKEND}/api/investigations/stream?${params}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    // ── STAGE_CHANGED ────────────────────────────────────────────
    es.addEventListener('STAGE_CHANGED', (e: MessageEvent) => {
      try {
        const d: StageChangedPayload = JSON.parse(e.data)
        setStage(d.stage_name)
        addLog('STAGE', `${d.stage_name} — ${d.description}`)
      } catch { /* ignore malformed */ }
    })

    // ── CONSUMERS_FOUND ──────────────────────────────────────────
    es.addEventListener('CONSUMERS_FOUND', (e: MessageEvent) => {
      try {
        const d: ConsumersFoundPayload = JSON.parse(e.data)
        // Mark all direct consumers as EVALUATING immediately
        setNodeStates(prev => {
          const next = { ...prev }
          d.consumer_service_ids.forEach(id => {
            next[id] = { status: 'EVALUATING' }
          })
          return next
        })
        addLog('DISCOVER', `Found ${d.consumer_service_ids.length} consumer(s) of ${d.api_id}`)
      } catch { /* ignore */ }
    })

    // ── COMPATIBILITY_CHECKED ────────────────────────────────────
    es.addEventListener('COMPATIBILITY_CHECKED', (e: MessageEvent) => {
      try {
        const d: CompatibilityCheckedPayload = JSON.parse(e.data)
        const status = toNodeStatus(d.status)
        setNodeStates(prev => ({
          ...prev,
          [d.service_id]: { status, reason: d.missing_claims.join(', ') || undefined },
        }))
        const icon = d.status === 'INCOMPATIBLE' ? '✗' : '✓'
        addLog('COMPAT', `${icon} ${d.service_name} — ${d.status}${d.missing_claims.length ? ` (missing: ${d.missing_claims.join(', ')})` : ''}`)
      } catch { /* ignore */ }
    })

    // ── DOWNSTREAM_PATH ──────────────────────────────────────────
    es.addEventListener('DOWNSTREAM_PATH', (e: MessageEvent) => {
      try {
        const d: DownstreamPathPayload = JSON.parse(e.data)
        // Mark downstream services as POTENTIAL_DOWNSTREAM
        const leafId = d.path[0]
        if (leafId) {
          setNodeStates(prev => ({
            ...prev,
            [leafId]: { status: 'POTENTIAL_DOWNSTREAM' },
          }))
        }
        addLog('PATH', `Depth ${d.depth}: ${d.path.join(' → ')}`)
      } catch { /* ignore */ }
    })

    // ── MEMORY_RECALLED ──────────────────────────────────────────
    es.addEventListener('MEMORY_RECALLED', (e: MessageEvent) => {
      try {
        const d: MemoryRecalledPayload = JSON.parse(e.data)
        addLog('MEMORY', `Recalled ${d.findings_count} prior finding(s) with temporal decay`)
      } catch { /* ignore */ }
    })

    // ── FINDING_PRODUCED ─────────────────────────────────────────
    es.addEventListener('FINDING_PRODUCED', (e: MessageEvent) => {
      try {
        const d: FindingProducedPayload = JSON.parse(e.data)
        const status = toNodeStatus(d.status)
        setNodeStates(prev => ({
          ...prev,
          [d.service_id]: { status },
        }))
        const pct = Math.round(d.confidence * 100)
        addLog('FINDING', `${d.service_name ?? d.service_id} → ${d.status.toUpperCase()} (${pct}% confidence)`)
      } catch { /* ignore */ }
    })

    // ── COMPLETE ─────────────────────────────────────────────────
    es.addEventListener('COMPLETE', (e: MessageEvent) => {
      try {
        const d: CompletePayload = JSON.parse(e.data)
        setStreamSummary(d)
        setIsComplete(true)
        setIsRunning(false)
        addLog('COMPLETE', `Done in ${d.execution_time_ms.toFixed(0)}ms — ${d.summary.incompatible} incompatible, ${d.summary.potential_downstream} downstream`)
        es.close()
        eventSourceRef.current = null
      } catch { /* ignore */ }
    })

    // ── Connection error ─────────────────────────────────────────
    es.onerror = () => {
      addLog('ERROR', 'Stream connection lost')
      setIsRunning(false)
      es.close()
      eventSourceRef.current = null
    }
  }, [stopStream, addLog])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  return { nodeStates, logs, stage, isRunning, isComplete, streamSummary, startStream, stopStream }
}

