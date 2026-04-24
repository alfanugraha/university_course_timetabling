import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export type HariOption = 'Senin' | 'Selasa' | 'Rabu' | 'Kamis' | 'Jumat'

export interface Timeslot {
  id: string
  kode: string
  hari: string
  sesi: number
  jam_mulai: string
  jam_selesai: string
  label: string
  sks: number
}

export interface TimeslotUpdatePayload {
  kode?: string
  hari?: string
  sesi?: number
  jam_mulai?: string
  jam_selesai?: string
  label?: string
  sks?: number
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getTimeslots(): Promise<Timeslot[]> {
  const res = await apiClient.get<Timeslot[]>('/timeslot')
  return res.data
}

export async function updateTimeslot(id: string, data: TimeslotUpdatePayload): Promise<Timeslot> {
  const res = await apiClient.put<Timeslot>(`/timeslot/${id}`, data)
  return res.data
}
