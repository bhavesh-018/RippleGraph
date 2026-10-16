import type { TopologyResponse, Investigation, ChangeProposal, EvidenceResult, MemoryComparisonResponse, InvestigationHistoryResponse } from '../types'

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getTopology: () =>
    fetchJSON<TopologyResponse>('/api/graph/topology'),

  getChanges: () =>
    fetchJSON<ChangeProposal[]>('/api/changes'),

  getInvestigations: () =>
    fetchJSON<Investigation[]>('/api/investigations'),

  getInvestigation: (id: string) =>
    fetchJSON<Investigation>(`/api/investigations/${id}`),

  startInvestigation: (changeId: string, memoryEnabled: boolean, disconnectGraph: boolean = false) =>
    fetchJSON<Investigation>('/api/investigations', {
      method: 'POST',
      body: JSON.stringify({
        change_id: changeId,
        memory_enabled: memoryEnabled,
        disconnect_graph: disconnectGraph,
      }),
    }),

  getFindingEvidence: (investigationId: string, findingId: string) =>
    fetchJSON<EvidenceResult>(`/api/investigations/${investigationId}/findings/${findingId}/evidence`),

  compareMemory: (changeId: string = 'CHG-001') =>
    fetchJSON<MemoryComparisonResponse>('/api/investigations/compare', {
      method: 'POST',
      body: JSON.stringify({ change_id: changeId }),
    }),

  getHistory: (limit: number = 50) =>
    fetchJSON<InvestigationHistoryResponse>(`/api/investigations/history?limit=${limit}`),
}

