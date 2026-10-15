import { useState, useCallback } from 'react'
import './index.css'

import LeftPanel from './components/LeftPanel'
import CenterGraph from './components/CenterGraph'
import RightPanel from './components/RightPanel'
import { api } from './api/client'
import type { Finding } from './types'
import type { NodeStateMap } from './api/sse'

function App() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [nodeStates, setNodeStates] = useState<NodeStateMap>({})
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [stage] = useState('')

  const handleRunInvestigation = useCallback(async (changeId: string, memoryEnabled: boolean) => {
    try {
      setFindings([])
      setNodeStates({})
      setIsComplete(false)
      setIsRunning(true)

      const result = await api.startInvestigation(changeId, memoryEnabled)
      const rawFindings: Finding[] = (result as any).findings ?? []
      setFindings(rawFindings)

      // Build node state map from findings → drives node border colors
      const states: NodeStateMap = {}
      rawFindings.forEach(f => {
        states[f.service_id] = {
          status: f.status.toUpperCase() as any,
        }
      })
      setNodeStates(states)
      setIsComplete(true)
    } catch (err) {
      console.error('Failed to start investigation:', err)
    } finally {
      setIsRunning(false)
    }
  }, [])

  return (
    <div className="app-layout">
      <LeftPanel
        onRunInvestigation={handleRunInvestigation}
        isRunning={isRunning}
        stage={stage}
      />

      <main className="center-panel">
        <CenterGraph nodeStates={nodeStates} />
      </main>

      <RightPanel
        logs={[]}
        findings={findings}
        isRunning={isRunning}
        isComplete={isComplete}
      />
    </div>
  )
}

export default App
