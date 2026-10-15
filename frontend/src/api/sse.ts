import { useEffect, useRef, useCallback, useState } from 'react'
import type { SSEEvent, NodeStatus } from '../types'

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

// ── Hook Return ──────────────────────────────────────────────────
interface UseInvestigationStreamReturn {
  nodeStates: NodeStateMap
  logs: LogEntry[]
  stage: string
  isRunning: boolean
  isComplete: boolean
  startStream: (investigationId: string) => void
  stopStream: () => void
}

let logCounter = 0

export function useInvestigationStream(): UseInvestigationStreamReturn {
  const [nodeStates, setNodeStates] = useState<NodeStateMap>({})
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [stage, setStage] = useState<string>('')
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const addLog = useCallback((type: string, message: string) => {
    const entry: LogEntry = {
      id: `log-${++logCounter}`,
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      type,
      message,
    }
    setLogs(prev => [...prev, entry])
  }, [])

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsRunning(false)
  }, [])

  const startStream = useCallback((investigationId: string) => {
    // Reset state
    stopStream()
    setNodeStates({})
    setLogs([])
    setStage('')
    setIsComplete(false)
    setIsRunning(true)

    addLog('SYSTEM', `Starting investigation stream: ${investigationId}`)

    const es = new EventSource(`/api/investigations/${investigationId}/stream`)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'PIPELINE_STAGE':
            setStage(data.stage as string)
            addLog('STAGE', `Entering stage: ${data.stage}`)
            break

          case 'NODE_EVALUATING':
            setNodeStates(prev => ({
              ...prev,
              [data.nodeId as string]: { status: 'EVALUATING' },
            }))
            addLog('EVAL', `Evaluating: ${data.nodeId}`)
            break

          case 'NODE_STATUS_CHANGE':
            setNodeStates(prev => ({
              ...prev,
              [data.nodeId as string]: {
                status: data.status as NodeStatus,
                reason: data.reason as string,
              },
            }))
            addLog('STATUS', `${data.nodeId}: ${data.status}`)
            break

          case 'EDGE_PULSE':
            addLog('EDGE', `Traversing: ${data.source} → ${data.target}`)
            break

          case 'MEMORY_RETRIEVED':
            addLog('MEMORY', `Retrieved ${data.count} prior findings`)
            break

          case 'REVIEWER_DECISION':
            addLog('REVIEW', `${data.findingId}: ${data.decision} - ${data.rationale}`)
            break

          case 'INVESTIGATION_COMPLETE':
            setIsComplete(true)
            setIsRunning(false)
            addLog('COMPLETE', 'Investigation finished')
            es.close()
            break

          default:
            addLog('EVENT', JSON.stringify(data))
        }
      } catch {
        addLog('ERROR', `Failed to parse event: ${event.data}`)
      }
    }

    es.onerror = () => {
      addLog('ERROR', 'Stream connection lost')
      setIsRunning(false)
      es.close()
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

  return { nodeStates, logs, stage, isRunning, isComplete, startStream, stopStream }
}
