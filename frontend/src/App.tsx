import { useState, useCallback } from 'react'
import './index.css'

import TopNav from './components/TopNav'
import LeftPanel from './components/LeftPanel'
import CenterGraph from './components/CenterGraph'
import RightPanel from './components/RightPanel'
import { api } from './api/client'
import type { Finding, ChangeProposal, RedHerring, Investigation } from './types'
import type { NodeStateMap } from './api/sse'

function App() {
  const [selectedChange, setSelectedChange] = useState<ChangeProposal | undefined>(undefined)
  const [findings, setFindings] = useState<Finding[]>([])
  const [redHerrings, setRedHerrings] = useState<RedHerring[]>([])
  const [summary, setSummary] = useState<{
    incompatible: number
    potential_downstream: number
    compatible: number
    unaffected: number
  } | undefined>(undefined)
  const [nodeStates, setNodeStates] = useState<NodeStateMap>({})
  const [selectedServiceId, setSelectedServiceId] = useState<string | undefined>(undefined)
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [stage, setStage] = useState('')
  const [executionTimeMs, setExecutionTimeMs] = useState<number | undefined>(undefined)

  const handleRunInvestigation = useCallback(async (changeId: string, memoryEnabled: boolean) => {
    try {
      setFindings([])
      setRedHerrings([])
      setSummary(undefined)
      setNodeStates({})
      setIsComplete(false)
      setIsRunning(true)
      setStage('Stage 1: Investigator')

      // Trigger investigation on backend
      const result: Investigation = await api.startInvestigation(changeId, memoryEnabled)
      const rawFindings: Finding[] = result.findings ?? []
      setFindings(rawFindings)
      setRedHerrings(result.red_herrings_rejected ?? [])
      setSummary(result.summary)
      setExecutionTimeMs(result.execution_time_ms)

      // Build node state map to drive canvas colors & edges
      const states: NodeStateMap = {}
      rawFindings.forEach((f) => {
        states[f.service_id] = {
          status: f.status.toUpperCase() as any,
        }
      })
      setNodeStates(states)
      setIsComplete(true)
      setStage('Stage 4: Persist')
    } catch (err) {
      console.error('Failed to run investigation:', err)
    } finally {
      setIsRunning(false)
    }
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Top Header Bar */}
      <TopNav
        selectedChange={selectedChange}
        isRunning={isRunning}
        isComplete={isComplete}
        stage={stage}
        executionTimeMs={executionTimeMs}
      />

      {/* 3-Panel Main Shell */}
      <div className="app-layout" style={{ flex: 1, height: 'calc(100vh - 52px)' }}>
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
          findings={findings}
          redHerrings={redHerrings}
          summary={summary}
          isRunning={isRunning}
          isComplete={isComplete}
          selectedServiceId={selectedServiceId}
          onSelectService={setSelectedServiceId}
        />
      </div>
    </div>
  )
}

export default App
