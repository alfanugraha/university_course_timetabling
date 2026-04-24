import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export type RuangJenis = 'Kelas' | 'Lab' | 'Seminar'

export interface Ruang {
  id: string
  nama: string
  kapasitas: number
  lantai: number | null
  gedung: string | null
  jenis: RuangJenis
  is_active: boolean
}

export interface RuangCreatePayload {
  nama: string
  kapasitas?: number
  lantai?: number | null
  gedung?: string | null
  jenis?: RuangJenis
  is_active?: boolean
}

export interface RuangUpdatePayload extends Partial<RuangCreatePayload> {}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getRuang(): Promise<Ruang[]> {
  const res = await apiClient.get<Ruang[]>('/ruang')
  return res.data
}

export async function createRuang(data: RuangCreatePayload): Promise<Ruang> {
  const res = await apiClient.post<Ruang>('/ruang', data)
  return res.data
}

export async function updateRuang(id: string, data: RuangUpdatePayload): Promise<Ruang> {
  const res = await apiClient.put<Ruang>(`/ruang/${id}`, data)
  return res.data
}
