import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Kurikulum {
  id: string
  kode: string
  tahun: string
  prodi_id: string
  is_active: boolean
}

export interface KurikulumCreatePayload {
  kode: string
  tahun: string
  prodi_id: string
  is_active: boolean
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getKurikulum(): Promise<Kurikulum[]> {
  const res = await apiClient.get<Kurikulum[]>('/kurikulum')
  return res.data
}

export async function createKurikulum(data: KurikulumCreatePayload): Promise<Kurikulum> {
  const res = await apiClient.post<Kurikulum>('/kurikulum', data)
  return res.data
}

export async function updateKurikulum(id: string, data: Partial<KurikulumCreatePayload>): Promise<Kurikulum> {
  const res = await apiClient.put<Kurikulum>(`/kurikulum/${id}`, data)
  return res.data
}
