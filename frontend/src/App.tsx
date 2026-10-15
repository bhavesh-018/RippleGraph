import { useCallback, useState } from 'react'
import './index.css'

import TopNav from './components/TopNav'
import LeftPanel from './components/LeftPanel'
import CenterGraph from './components/CenterGraph'
import RightPanel from './components/RightPanel'
import { useInvestigationStream } from './api/sse'
import type { ChangeProposal } from './types'

function App() {
  const [selectedChange, setSelectedChange] = useState<ChangeProposal | undefined>(undefined)
  const [selectedServiceId, setSelectedServiceId] = useState<string | undefined>(undefined)
  const [disconnectGraph, setDisconnectGraph] = useState(false)

  const {
    nodeStates,
    stage,
    isRunning,
    isComplete,
    streamSummary,
    startStream,
    stopStream,
  } = useInvestigationStream()

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
          findings={[]}
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

