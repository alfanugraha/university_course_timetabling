import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export type SesiStatus = 'Draft' | 'Aktif' | 'Disetujui' | 'Arsip'
export type SesiSemester = 'Ganjil' | 'Genap'

export interface SesiJadwal {
  id: string
  nama: string
  semester: SesiSemester
  tahun_akademik: string
  status: SesiStatus
  created_at: string
}

export interface SesiCreatePayload {
  nama: string
  semester: SesiSemester
  tahun_akademik: string
}

export interface ApprovePayload {
  minta_revisi?: boolean
  catatan?: string | null
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getSesiList(): Promise<SesiJadwal[]> {
  const res = await apiClient.get<SesiJadwal[]>('/sesi')
  return res.data
}

export async function createSesi(data: SesiCreatePayload): Promise<SesiJadwal> {
  const res = await apiClient.post<SesiJadwal>('/sesi', data)
  return res.data
}

export async function approveSesi(id: string, payload?: ApprovePayload): Promise<SesiJadwal> {
  const res = await apiClient.patch<SesiJadwal>(`/sesi/${id}/approve`, payload ?? {})
  return res.data
}

export async function publishSesi(id: string): Promise<SesiJadwal> {
  const res = await apiClient.patch<SesiJadwal>(`/sesi/${id}/publish`)
  return res.data
}
