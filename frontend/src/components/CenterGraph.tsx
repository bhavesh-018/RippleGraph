import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  MarkerType,
  type Node,
  type Edge,
} from 'reactflow'
import dagre from '@dagrejs/dagre'
import 'reactflow/dist/style.css'
import ServiceNode from './ServiceNode'
import { api } from '../api/client'
import type { ServiceData, NodeStatus } from '../types'
import type { NodeStateMap } from '../api/sse'

const NODE_W = 240
const NODE_H = 120

// Layout graph from Provider (Root) -> Consumers (Downstream)
function applyDagreLayout(nodes: Node<ServiceData>[], edges: Edge[]): Node<ServiceData>[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 50, ranksep: 80 })

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))

  // DEPENDS_ON edge is (caller)->(provider).
  // For blast radius visualization, layout flows provider -> caller:
  edges.forEach((e) => g.setEdge(e.target, e.source))

  dagre.layout(g)

  return nodes.map((n) => {
    const nodeWithPosition = g.node(n.id)
    return {
      ...n,
      position: {
        x: nodeWithPosition ? nodeWithPosition.x - NODE_W / 2 : 0,
        y: nodeWithPosition ? nodeWithPosition.y - NODE_H / 2 : 0,
      },
    }
  })
}

const nodeTypes = { serviceNode: ServiceNode }

interface CenterGraphProps {
  nodeStates?: NodeStateMap
  originServiceId?: string
  selectedServiceId?: string
  onSelectService?: (serviceId: string) => void
}

export default function CenterGraph({
  nodeStates = {},
  originServiceId = 'auth-service',
  selectedServiceId,
  onSelectService,
}: CenterGraphProps) {
  const [nodes, setNodes] = useState<Node<ServiceData>[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [loading, setLoading] = useState(true)

  // Load topology from backend
  const loadTopology = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.getTopology()

      const rawNodes: Node<ServiceData>[] = data.nodes.map((n) => ({
        id: n.id,
        position: n.position,
        type: 'serviceNode',
        data: {
          ...n.data,
          status: 'UNAFFECTED',
          isOrigin: n.id === originServiceId,
        },
      }))

      const rawEdges: Edge[] = data.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#3F3F46', strokeWidth: 1.5 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#3F3F46',
          width: 16,
          height: 16,
        },
      }))

      const layoutedNodes = applyDagreLayout(rawNodes, rawEdges)
      setNodes(layoutedNodes)
      setEdges(rawEdges)
    } catch (err) {
      console.error('Failed to load graph topology:', err)
    } finally {
      setLoading(false)
    }
  }, [originServiceId])

  useEffect(() => {
    loadTopology()
  }, [loadTopology])

  // React to investigation node state updates
  useEffect(() => {
    setNodes((currentNodes) =>
      currentNodes.map((n) => {
        const state = nodeStates[n.id]
        const status = state ? (state.status as NodeStatus) : (n.data.status || 'UNAFFECTED')
        const isOrigin = n.id === originServiceId

        return {
          ...n,
          selected: n.id === selectedServiceId,
          data: {
            ...n.data,
            status,
            isOrigin,
          },
        }
      })
    )

    // Update edge animations and colors based on node statuses
    setEdges((currentEdges) =>
      currentEdges.map((e) => {
        const sourceState = nodeStates[e.source]?.status
        const targetState = nodeStates[e.target]?.status

        const isBreaking = sourceState === 'INCOMPATIBLE' || targetState === 'INCOMPATIBLE'
        const isPotential =
          sourceState === 'POTENTIAL_DOWNSTREAM' ||
          sourceState === 'POTENTIAL' ||
          targetState === 'POTENTIAL_DOWNSTREAM' ||
          targetState === 'POTENTIAL'

        let stroke = '#27272A'
        let animated = false

        if (isBreaking) {
          stroke = '#EF4444'
          animated = true
        } else if (isPotential) {
          stroke = '#F59E0B'
          animated = true
        }

        return {
          ...e,
          animated,
          style: { stroke, strokeWidth: isBreaking || isPotential ? 2 : 1.5 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: stroke,
            width: 14,
            height: 14,
          },
        }
      })
    )
  }, [nodeStates, originServiceId, selectedServiceId])

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onSelectService) {
        onSelectService(node.id)
      }
    },
    [onSelectService]
  )

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#09090B' }}>
      {loading ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#71717A',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
          }}
        >
          Loading 10-Service Topology...
        </div>
      ) : (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.3}
          maxZoom={1.8}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1.5}
            color="rgba(255, 255, 255, 0.07)"
          />
          <Controls
            style={{
              background: '#141416',
              border: '1px solid #27272A',
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            }}
          />
          <MiniMap
            nodeColor={(n) => {
              const status = (n.data as ServiceData)?.status
              if ((n.data as ServiceData)?.isOrigin) return '#6366F1'
              if (status === 'EVALUATING') return '#06B6D4'
              if (status === 'INCOMPATIBLE') return '#EF4444'
              if (status === 'POTENTIAL' || status === 'POTENTIAL_DOWNSTREAM') return '#F59E0B'
              if (status === 'COMPATIBLE') return '#10B981'
              return '#27272A'
            }}
            style={{
              background: '#0D0D0F',
              border: '1px solid #27272A',
              borderRadius: '8px',
              width: 140,
              height: 90,
            }}
          />
        </ReactFlow>
      )}
    </div>
  )
}
