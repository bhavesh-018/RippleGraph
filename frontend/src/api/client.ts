import type { TopologyResponse, Investigation } from '../types'

// Uses Vite proxy in dev (/api → http://localhost:8000)
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

  getInvestigations: () =>
    fetchJSON<Investigation[]>('/api/investigations'),

  startInvestigation: (changeId: string, memoryEnabled: boolean) =>
    fetchJSON<Investigation>('/api/investigations', {
      method: 'POST',
      body: JSON.stringify({ change_id: changeId, memory_enabled: memoryEnabled }),
    }),
}
