import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DosenSksRekap {
  dosen_id: string
  dosen_nama: string
  dosen_kode: string
  total_sks: number
  breakdown: Record<string, number>
  bkd_limit_sks: number | null
  bkd_flag: 'ok' | 'near_limit' | 'over_limit' | 'no_limit'
}

export interface SksRekapResponse {
  sesi_id: string
  items: DosenSksRekap[]
  total_dosen: number
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getSksRekap(sesiId: string): Promise<SksRekapResponse> {
  const res = await apiClient.get<SksRekapResponse>(`/sesi/${sesiId}/reports/sks-rekap`)
  return res.data
}

// ─── Preferences Summary ──────────────────────────────────────────────────────

export interface DosenPreferenceSummaryItem {
  dosen_id: string
  kode: string
  nama: string
  total_preferensi: number
  total_dilanggar: number
}

export interface PreferencesSummaryResponse {
  sesi_id: string
  total_preferensi: number
  total_dilanggar: number
  breakdown: DosenPreferenceSummaryItem[]
}

export async function getPreferencesSummary(sesiId: string): Promise<PreferencesSummaryResponse> {
  const res = await apiClient.get<PreferencesSummaryResponse>(`/sesi/${sesiId}/preferences-summary`)
  return res.data
}

// ─── Room Map ─────────────────────────────────────────────────────────────────

export interface RoomCellInfo {
  kode_mk: string
  nama_mk: string
  kelas: string | null
  dosen: string
}

export interface RoomMapSlot {
  hari: string
  sesi: number
  label: string
  rooms: Record<string, RoomCellInfo | null>
}

export interface RoomMapResponse {
  sesi_id: string
  rooms: string[]
  days: string[]
  slots: RoomMapSlot[]
}

export async function getRoomMap(sesiId: string): Promise<RoomMapResponse> {
  const res = await apiClient.get<RoomMapResponse>(`/sesi/${sesiId}/reports/room-map`)
  return res.data
}
