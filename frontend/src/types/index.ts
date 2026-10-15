// RippleGraph - Frontend TypeScript Types

export type NodeStatus =
  | 'EVALUATING'
  | 'INCOMPATIBLE'
  | 'COMPATIBLE'
  | 'POTENTIAL'
  | 'POTENTIAL_DOWNSTREAM'
  | 'UNAFFECTED'

export interface ServiceData {
  id: string
  name: string
  label?: string
  tier: string | number
  owner_team: string
  repo?: string
  description?: string
  icon?: string
  runtime?: string
  version?: string
  port?: number
  status?: NodeStatus
  isOrigin?: boolean
  apis?: Array<{
    id: string
    name: string
    protocol: string
    path: string
  }>
  accepted_contracts?: Array<{
    contract_id: string
    version: string
  }>
}

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
    animated?: boolean
    data?: Record<string, unknown>
  }>
  total_services: number
  total_dependencies: number
}

export interface ChangeProposal {
  id: string
  title: string
  proposing_service: string
  proposing_service_name: string
  target_api: string
  target_api_name: string
  proposed_contract_id: string
  risk_level: string
  impact_scope: string
  claim_types: string[]
  description: string
}

export interface Finding {
  id: string
  investigation_id?: string
  service_id: string
  service_name?: string
  category: string
  status: string
  confidence: number
  reasons?: string[]
  missing_claims?: string[]
  dependency_chains?: string[][]
  hop_depth?: number
  recommended_mitigation_id?: string
  recommended_contract_id?: string
  relevant_incidents?: string[]
  rejected_red_herrings?: string[]
  created_at?: string
}

export interface RedHerring {
  incident_id: string
  title: string
  affected_service_id: string
  claim_types: string[]
  active_claim_types: string[]
  rationale: string
}

export interface Investigation {
  investigation_id: string
  change_id: string
  change_title: string
  memory_enabled: boolean
  disconnect_graph?: boolean
  warning?: string
  summary: {
    incompatible: number
    potential_downstream: number
    compatible: number
    unaffected: number
  }
  recommended_migration_contract?: string
  findings: Finding[]
  red_herrings_rejected?: RedHerring[]
  execution_time_ms?: number
}

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
