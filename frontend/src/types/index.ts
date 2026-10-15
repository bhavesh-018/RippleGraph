// ── Node Status ─────────────────────────────────────────────────
export type NodeStatus =
  | 'EVALUATING'
  | 'INCOMPATIBLE'
  | 'COMPATIBLE'
  | 'POTENTIAL'
  | 'UNAFFECTED'

// ── Service Data (attached to each graph node) ───────────────────
export interface ServiceData {
  id: string
  name: string
  tier: number
  owner_team: string
  repo?: string
  status?: NodeStatus
}

// ── Backend Topology Response ────────────────────────────────────
export interface TopologyResponse {
  nodes: Array<{
    id: string
    position: { x: number; y: number }
    data: ServiceData
  }>
  edges: Array<{
    id: string
    source: string
    target: string
    label?: string
  }>
}

// ── Investigation & Findings ─────────────────────────────────────
export interface Finding {
  id: string
  service_id: string
  service_name: string
  category: string
  status: string
  confidence: number
  summary: string
  created_at: string
}

export interface Investigation {
  investigation_id: string   // was: id
  change_id: string
  change_title: string       // add this
  status: string
  memory_enabled: boolean
  created_at: string
  findings?: Finding[]
}


// ── SSE Event Types ──────────────────────────────────────────────
export type SSEEventType =
  | 'PIPELINE_STAGE'
  | 'NODE_EVALUATING'
  | 'NODE_STATUS_CHANGE'
  | 'EDGE_PULSE'
  | 'MEMORY_RETRIEVED'
  | 'REVIEWER_DECISION'
  | 'INVESTIGATION_COMPLETE'

export interface SSEEvent {
  type: SSEEventType
  [key: string]: unknown
}
