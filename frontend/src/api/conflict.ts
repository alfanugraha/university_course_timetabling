import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConflictLog {
  id: string
  sesi_id: string
  jenis: string
  severity: 'ERROR' | 'WARNING'
  assignment_ids: string[]
  pesan: string
  detail: Record<string, unknown> | null
  checked_at: string
  is_resolved: boolean
}

export interface ConflictListParams {
  jenis?: string
  severity?: 'ERROR' | 'WARNING'
}

export interface ConflictSummary {
  total_error: number
  total_warning: number
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getConflicts(
  sesiId: string,
  params?: ConflictListParams
): Promise<ConflictLog[]> {
  const res = await apiClient.get<ConflictLog[]>(`/sesi/${sesiId}/conflicts`, { params })
  return res.data
}

export async function checkConflicts(sesiId: string): Promise<ConflictSummary> {
  const res = await apiClient.post<ConflictSummary>(`/sesi/${sesiId}/check-conflicts`)
  return res.data
}

export async function resolveConflict(
  sesiId: string,
  conflictId: string
): Promise<ConflictLog> {
  const res = await apiClient.patch<ConflictLog>(
    `/sesi/${sesiId}/conflicts/${conflictId}/resolve`
  )
  return res.data
}
