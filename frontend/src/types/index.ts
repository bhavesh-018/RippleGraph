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

// ── Legacy SSE types (kept for backward compatibility) ─────────────────────
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

// ── Backend-aligned SSE event payloads (Feature 1) ──────────────────────────
export type BackendSSEEventType =
  | 'STAGE_CHANGED'
  | 'CONSUMERS_FOUND'
  | 'COMPATIBILITY_CHECKED'
  | 'DOWNSTREAM_PATH'
  | 'MEMORY_RECALLED'
  | 'FINDING_PRODUCED'
  | 'COMPLETE'

export interface StageChangedPayload {
  stage_id: string
  stage_name: string
  description: string
}

export interface ConsumersFoundPayload {
  api_id: string
  consumer_service_ids: string[]
}

export interface CompatibilityCheckedPayload {
  service_id: string
  service_name: string
  status: 'COMPATIBLE' | 'INCOMPATIBLE'
  contract_id: string
  missing_claims: string[]
}

export interface DownstreamPathPayload {
  path: string[]
  depth: number
  status: string
}

export interface MemoryRecalledPayload {
  findings_count: number
  prior_finding_ids: string[]
  applied_to_services: string[]
}

export interface FindingProducedPayload {
  finding_id: string
  service_id: string
  service_name?: string
  category: string
  status: string
  confidence: number
  hop_depth: number
}

export interface CompletePayload {
  investigation_id: string
  change_id: string
  summary: {
    incompatible: number
    potential_downstream: number
    compatible: number
    unaffected: number
  }
  recommended_contract?: string
  execution_time_ms: number
}

export interface BackendSSEMessage<T = unknown> {
  event: BackendSSEEventType
  data: T
}

// ── Feature 3: Evidence Path Inspector ──────────────────────────────────────
export interface EvidenceIncident {
  id: string
  title: string
  severity: string
  description: string
  occurred_at: string
  mitigation: {
    id: string
    title: string
    description: string
    validation_method: string
  } | null
}

export interface EvidenceResult {
  finding: {
    id: string
    service_id: string
    service_name: string
    category: string
    status: string
    confidence: number
    reasons: string[]
    missing_claims: string[]
    dependency_chains: string[][]
    hop_depth: number
    relevant_incidents: string[]
    recommended_contract_id: string | null
  }
  service: {
    id: string
    name: string
    tier: string
    owner_team: string
    description: string
    runtime: string
    port: number
  } | null
  incidents: EvidenceIncident[]
  contract: {
    id: string
    version: string
    description: string
    status: string
  } | null
}

// ── Feature 2: Memory Comparison & Visual Diff ──────────────────────────────
export interface ServiceMemoryDelta {
  service_id: string
  service_name: string
  status_with_memory: string
  status_without_memory: string
  confidence_with_memory: number
  confidence_without_memory: number
  confidence_delta: number
  confidence_gain_pct: number
  memory_reaffirmed: boolean
  prior_finding_cited?: string | null
  prior_investigation_id?: string | null
  memory_explanation?: string | null
  missing_claims: string[]
}

export interface MemoryComparisonSummary {
  change_id: string
  change_title: string
  avg_confidence_with_memory: number
  avg_confidence_without_memory: number
  avg_confidence_delta: number
  overall_confidence_gain_pct: number
  reaffirmed_count: number
  total_services_analyzed: number
  execution_time_with_memory_ms: number
  execution_time_without_memory_ms: number
  memory_verdict: string
}

export interface MemoryComparisonResponse {
  change_id: string
  summary: MemoryComparisonSummary
  deltas: ServiceMemoryDelta[]
  investigation_id_with_memory: string
  investigation_id_without_memory: string
}


