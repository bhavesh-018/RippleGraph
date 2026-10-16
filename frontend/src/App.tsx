import { useCallback, useState, useEffect, useRef } from 'react'
import './index.css'

import TopNav from './components/TopNav'
import LeftPanel from './components/LeftPanel'
import CenterGraph from './components/CenterGraph'
import RightPanel from './components/RightPanel'
import StreamLog from './components/StreamLog'
import EvidenceModal from './components/EvidenceModal'
import MemoryDiffModal from './components/MemoryDiffModal'
import HistoryPanel from './components/HistoryPanel'
import { useInvestigationStream } from './api/sse'
import { api } from './api/client'
import type { ChangeProposal, Finding, InvestigationSummary } from './types'

function App() {
  const [selectedChange, setSelectedChange] = useState<ChangeProposal | undefined>(undefined)
  const [selectedServiceId, setSelectedServiceId] = useState<string | undefined>(undefined)
  const [disconnectGraph, setDisconnectGraph] = useState(false)

  // Evidence modal state — null means closed
  const [evidenceFinding, setEvidenceFinding] = useState<Finding | null>(null)

  // Memory comparison modal state — null means closed
  const [compareChangeId, setCompareChangeId] = useState<string | null>(null)

  // History timeline panel state
  const [showHistory, setShowHistory] = useState(false)
  const [replayedInvestigationId, setReplayedInvestigationId] = useState<string | null>(null)

  // Rich findings: fetched from DB after SSE completes (have real FND-xxx IDs)
  const [richFindings, setRichFindings] = useState<Finding[]>([])

  const {
    nodeStates,
    logs,
    stage,
    isRunning,
    isComplete,
    streamSummary,
    startStream,
    stopStream,
  } = useInvestigationStream()

  const [streamFindings, setStreamFindings] = useState<Finding[]>([])
  const prevIsRunning = useRef(false)

  // Reset on new stream start
  useEffect(() => {
    if (isRunning && !prevIsRunning.current) {
      setStreamFindings([])
      setRichFindings([])
      setEvidenceFinding(null)
    }
    prevIsRunning.current = isRunning
  }, [isRunning])

  // Build live findings from SSE node states during run
  useEffect(() => {
    if (!isRunning && !isComplete) return
    const produced: Finding[] = Object.entries(nodeStates)
      .filter(([, s]) => s.status !== 'EVALUATING' && s.status !== 'UNAFFECTED')
      .map(([serviceId, s], idx) => ({
        id: `live-${serviceId}`,
        service_id: serviceId,
        service_name: serviceId,
        category: 'CONTRACT_COMPATIBILITY',
        status: s.status.toLowerCase(),
        confidence: s.status === 'INCOMPATIBLE' ? 0.91 : s.status === 'COMPATIBLE' ? 0.85 : 0.72,
        hop_depth: idx,
      } as Finding))
    setStreamFindings(produced)
  }, [nodeStates, isRunning, isComplete])

  // After SSE completes → fetch real findings (with real FND-xxx IDs from FalkorDB)
  useEffect(() => {
    if (!isComplete || !streamSummary?.investigation_id) return
    api.getInvestigation(streamSummary.investigation_id)
      .then(inv => {
        if (inv.findings && inv.findings.length > 0) {
          setRichFindings(inv.findings)
        }
      })
      .catch(err => console.error('Failed to fetch rich findings:', err))
  }, [isComplete, streamSummary])

  const handleRunInvestigation = useCallback((changeId: string, memoryEnabled: boolean) => {
    startStream({ changeId, memoryEnabled, disconnectGraph, paceDelayS: 0.35 })
  }, [startStream, disconnectGraph])

  const summary = streamSummary?.summary
  const executionTimeMs = streamSummary?.execution_time_ms
  const investigationId = streamSummary?.investigation_id

  // Use real DB findings when available, fall back to live SSE findings
  const findings = richFindings.length > 0 ? richFindings : streamFindings

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      <TopNav
        selectedChange={selectedChange}
        isRunning={isRunning}
        isComplete={isComplete}
        stage={stage}
        executionTimeMs={executionTimeMs}
        disconnectGraph={disconnectGraph}
        onToggleDisconnectGraph={() => setDisconnectGraph((prev) => !prev)}
      />

      <div className="app-layout" style={{ flex: 1, height: 'calc(100vh - 48px)' }}>
        <LeftPanel
          onRunInvestigation={handleRunInvestigation}
          isRunning={isRunning}
          stage={stage}
          selectedChange={selectedChange}
          onSelectChange={setSelectedChange}
          onCompareMemory={setCompareChangeId}
          onOpenHistory={() => setShowHistory(true)}
        />

        <main className="center-panel">
          <CenterGraph
            nodeStates={nodeStates}
            originServiceId={selectedChange?.proposing_service || 'auth-service'}
            selectedServiceId={selectedServiceId}
            onSelectService={setSelectedServiceId}
          />
          <StreamLog
            logs={logs}
            isRunning={isRunning}
            isComplete={isComplete}
            stage={stage}
          />
        </main>

        <RightPanel
          findings={findings}
          redHerrings={[]}
          summary={summary}
          isRunning={isRunning}
          isComplete={isComplete}
          selectedServiceId={selectedServiceId}
          onSelectService={setSelectedServiceId}
          disconnectGraph={disconnectGraph}
          investigationId={investigationId}
          onInspectFinding={setEvidenceFinding}
        />
      </div>

      {/* Evidence Path Inspector Modal */}
      {evidenceFinding && investigationId && (
        <EvidenceModal
          finding={evidenceFinding}
          investigationId={investigationId}
          onClose={() => setEvidenceFinding(null)}
        />
      )}

      {/* Memory Comparison & Visual Diff Modal */}
      {compareChangeId && (
        <MemoryDiffModal
          changeId={compareChangeId}
          onClose={() => setCompareChangeId(null)}
        />
      )}

      {/* Investigation History Timeline */}
      {showHistory && (
        <HistoryPanel
          onClose={() => setShowHistory(false)}
          activeInvestigationId={replayedInvestigationId ?? investigationId ?? null}
          onReplay={(summary: InvestigationSummary) => {
            setReplayedInvestigationId(summary.investigation_id)
            // Load investigation findings from DB and surface them in RightPanel
            api.getInvestigation(summary.investigation_id)
              .then(inv => {
                if (inv.findings && inv.findings.length > 0) {
                  setRichFindings(inv.findings as Finding[])
                }
              })
              .catch(err => console.error('Replay load failed:', err))
            setShowHistory(false)
          }}
        />
      )}
    </div>
  )
}

export default App
