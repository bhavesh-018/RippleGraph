import './index.css'

function App() {
  return (
    <div className="app-layout">

      {/* ── Left Panel: Controls ── */}
      <aside className="left-panel">
        <div className="panel-header">
          <span className="app-logo">RippleGraph</span>
        </div>
        <div className="panel-body">
          <p className="text-muted text-sm">Change controls — coming in C28</p>
        </div>
      </aside>

      {/* ── Center: Graph Canvas ── */}
      <main className="center-panel">
        <div className="center-placeholder">
          <p className="text-secondary text-sm">Graph canvas — coming in C29</p>
        </div>
      </main>

      {/* ── Right Panel: Findings & Logs ── */}
      <aside className="right-panel">
        <div className="panel-header">
          <span className="text-primary font-semibold text-md">Findings</span>
        </div>
        <div className="panel-body">
          <p className="text-muted text-sm">Run an investigation to see findings</p>
        </div>
      </aside>

    </div>
  )
}

export default App
