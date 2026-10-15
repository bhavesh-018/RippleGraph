import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  BackgroundVariant,
  type Node,
  type Edge,
} from 'reactflow'
import dagre from '@dagrejs/dagre'
import 'reactflow/dist/style.css'
import ServiceNode from './ServiceNode'


import { api } from '../api/client'
import type { ServiceData } from '../types'

// ── Dagre Layout ─────────────────────────────────────────────────
const NODE_W = 160
const NODE_H = 56

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 70, ranksep: 90 })

  nodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  edges.forEach(e => g.setEdge(e.source, e.target))

  dagre.layout(g)

  return nodes.map(n => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 } }
  })
}

// ── Default node style (C30 replaces with custom ServiceNode) ─────
const defaultNodeStyle = {
  background: '#141414',
  border: '1px solid #2A2A2A',
  borderRadius: '6px',
  color: '#EDEDED',
  fontSize: '12px',
  padding: '8px 12px',
  fontFamily: "'Inter', sans-serif",
}

// ── Custom node types registry ───────────────────────────────────
const nodeTypes = { serviceNode: ServiceNode }

// ── Component ────────────────────────────────────────────────────
export default function CenterGraph() {
  const [nodes, setNodes] = useState<Node<ServiceData>[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTopology = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getTopology()

      const rfNodes: Node<ServiceData>[] = data.nodes.map(n => ({
        id: n.id,
        position: n.position,
        type: 'serviceNode',
        data: n.data,
        style: defaultNodeStyle,
        // label shown until C30's custom node takes over
        ...(n.data?.name ? { data: { ...n.data, label: n.data.name } } : {}),
      }))

      const rfEdges: Edge[] = data.edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        style: { stroke: '#2A2A2A', strokeWidth: 1 },
        animated: false,
      }))

      const layoutedNodes = applyDagreLayout(rfNodes, rfEdges)
      setNodes(layoutedNodes)
      setEdges(rfEdges)
    } catch (err) {
      setError('Could not connect to backend. Is the API server running?')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTopology()
  }, [loadTopology])

  if (loading) {
    return (
      <div className="center-placeholder">
        <p className="text-secondary text-sm">Loading graph topology...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="center-placeholder" style={{ flexDirection: 'column', gap: '8px' }}>
        <p className="text-sm" style={{ color: 'var(--status-incompatible-text)' }}>
          {error}
        </p>
        <button
          onClick={loadTopology}
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-active)',
            color: 'var(--text-secondary)',
            borderRadius: 'var(--radius-md)',
            padding: '4px 12px',
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#1F1F1F"
        />
        <Controls
          style={{
            background: '#111111',
            border: '1px solid #1F1F1F',
            borderRadius: '6px',
          }}
        />
      </ReactFlow>
    </div>
  )
}
