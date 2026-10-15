import { useCallback, useState, useEffect, useRef } from 'react'
import './index.css'

import TopNav from './components/TopNav'
import LeftPanel from './components/LeftPanel'
import CenterGraph from './components/CenterGraph'
import RightPanel from './components/RightPanel'
import { useInvestigationStream } from './api/sse'
import type { ChangeProposal, Finding } from './types'

function App() {
  const [selectedChange, setSelectedChange] = useState<ChangeProposal | undefined>(undefined)
  const [selectedServiceId, setSelectedServiceId] = useState<string | undefined>(undefined)
  const [disconnectGraph, setDisconnectGraph] = useState(false)

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

  // Build a live findings list from nodeStates as FINDING_PRODUCED events arrive.
  // We derive findings from nodeStates so they update reactively without extra state.
  const [streamFindings, setStreamFindings] = useState<Finding[]>([])
  const prevIsRunning = useRef(false)

  // Reset findings when a new stream starts
  useEffect(() => {
    if (isRunning && !prevIsRunning.current) {
      setStreamFindings([])
    }
    prevIsRunning.current = isRunning
  }, [isRunning])

  // Accumulate findings: whenever nodeStates changes during a run,
  // synthesize Finding objects from the FINDING_PRODUCED entries.
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

  const handleRunInvestigation = useCallback((changeId: string, memoryEnabled: boolean) => {
    startStream({
      changeId,
      memoryEnabled,
      disconnectGraph,
      paceDelayS: 0.35,
    })
  }, [startStream, disconnectGraph])

  // Derive findings + summary from the COMPLETE SSE event payload
  const summary = streamSummary?.summary
  const executionTimeMs = streamSummary?.execution_time_ms

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Top Header Bar */}
      <TopNav
        selectedChange={selectedChange}
        isRunning={isRunning}
        isComplete={isComplete}
        stage={stage}
        executionTimeMs={executionTimeMs}
        disconnectGraph={disconnectGraph}
        onToggleDisconnectGraph={() => setDisconnectGraph((prev) => !prev)}
      />

      {/* 3-Panel Main Shell */}
      <div className="app-layout" style={{ flex: 1, height: 'calc(100vh - 48px)' }}>
        <LeftPanel
          onRunInvestigation={handleRunInvestigation}
          isRunning={isRunning}
          logs={logs}
          stage={stage}
          selectedChange={selectedChange}
          onSelectChange={setSelectedChange}
        />

        <main className="center-panel">
          <CenterGraph
            nodeStates={nodeStates}
            originServiceId={selectedChange?.proposing_service || 'auth-service'}
            selectedServiceId={selectedServiceId}
            onSelectService={setSelectedServiceId}
          />
        </main>

        <RightPanel
          findings={streamFindings}
          redHerrings={[]}
          summary={summary}
          isRunning={isRunning}
          isComplete={isComplete}
          selectedServiceId={selectedServiceId}
          onSelectService={setSelectedServiceId}
          disconnectGraph={disconnectGraph}
        />
      </div>
    </div>
  )
}

export default App

