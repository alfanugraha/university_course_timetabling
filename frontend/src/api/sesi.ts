import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export type SesiStatus = 'Draft' | 'Aktif' | 'Arsip'
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

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getSesiList(): Promise<SesiJadwal[]> {
  const res = await apiClient.get<SesiJadwal[]>('/sesi')
  return res.data
}

export async function createSesi(data: SesiCreatePayload): Promise<SesiJadwal> {
  const res = await apiClient.post<SesiJadwal>('/sesi', data)
  return res.data
}
