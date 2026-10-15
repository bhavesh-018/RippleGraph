import { useState, useCallback } from 'react'
import './index.css'

import LeftPanel from './components/LeftPanel'
import CenterGraph from './components/CenterGraph'
import RightPanel from './components/RightPanel'
import { api } from './api/client'
import type { Finding } from './types'

function App() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [stage] = useState('')

  const handleRunInvestigation = useCallback(async (changeId: string, memoryEnabled: boolean) => {
    try {
      setFindings([])
      setIsComplete(false)
      setIsRunning(true)
      // Pipeline runs synchronously — full result comes back in the POST response
      const result = await api.startInvestigation(changeId, memoryEnabled)
      const rawFindings = (result as any).findings ?? []
      setFindings(rawFindings)
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
        <CenterGraph nodeStates={{}} />
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
