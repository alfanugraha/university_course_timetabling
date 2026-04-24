import apiClient from './client'

export interface Dosen {
  id: string
  kode: string
  nama: string
  nidn: string | null
  nip: string | null
  jabfung: string | null
  kjfd: string | null
  homebase_prodi_id: string | null
  bkd_limit_sks: number | null
  tgl_lahir: string | null
  status: 'Aktif' | 'Non-Aktif' | 'Pensiun'
  user_id: string | null
}

export interface DosenCreatePayload {
  kode: string
  nama: string
  nidn?: string | null
  nip?: string | null
  jabfung?: string | null
  kjfd?: string | null
  homebase_prodi_id?: string | null
  bkd_limit_sks?: number | null
  tgl_lahir?: string | null
  status?: string
  user_id?: string | null
}

export interface DosenUpdatePayload extends Partial<DosenCreatePayload> {}

export interface DosenListParams {
  status?: string
  homebase_prodi_id?: string
}

export async function getDosen(params?: DosenListParams): Promise<Dosen[]> {
  const res = await apiClient.get<Dosen[]>('/dosen', { params })
  return res.data
}

export async function createDosen(data: DosenCreatePayload): Promise<Dosen> {
  const res = await apiClient.post<Dosen>('/dosen', data)
  return res.data
}

export async function updateDosen(id: string, data: DosenUpdatePayload): Promise<Dosen> {
  const res = await apiClient.put<Dosen>(`/dosen/${id}`, data)
  return res.data
}

// ─── Jadwal Dosen ─────────────────────────────────────────────────────────────

export interface DosenJadwalItem {
  id: string
  mk_kelas: {
    id: string
    label: string
    kelas: string | null
    mata_kuliah_kode: string
    mata_kuliah_nama: string
    semester: number
    sks: number
    prodi: { id: string; kode: string; nama: string; singkat: string }
  }
  dosen1: { id: string; kode: string; nama: string }
  dosen2: { id: string; kode: string; nama: string } | null
  timeslot: {
    id: string
    kode: string
    hari: string
    sesi: number
    jam_mulai: string
    jam_selesai: string
    label: string
  }
  ruang: { id: string; nama: string; kapasitas: number; lantai: number | null; gedung: string | null } | null
}

export interface DosenJadwalResponse {
  items: DosenJadwalItem[]
  total: number
  page: number
  page_size: number
}

export async function getDosenJadwal(sesiId: string): Promise<DosenJadwalResponse> {
  const res = await apiClient.get<DosenJadwalResponse>(`/sesi/${sesiId}/assignments`, {
    params: { page: 1, page_size: 100 },
  })
  return res.data
}

// ─── Unavailability ───────────────────────────────────────────────────────────

export interface DosenUnavailabilityItem {
  id: string
  dosen_id: string
  timeslot_id: string
  sesi_id: string | null
  catatan: string | null
  created_at: string
  timeslot: {
    id: string
    kode: string
    hari: string
    sesi: number
    jam_mulai: string
    jam_selesai: string
    label: string
  } | null
}

export async function getDosenUnavailability(dosenId: string): Promise<DosenUnavailabilityItem[]> {
  const res = await apiClient.get<DosenUnavailabilityItem[]>(`/dosen/${dosenId}/unavailability`)
  return res.data
}

export async function addDosenUnavailability(
  dosenId: string,
  timeslotId: string,
  catatan?: string
): Promise<DosenUnavailabilityItem> {
  const res = await apiClient.post<DosenUnavailabilityItem>(`/dosen/${dosenId}/unavailability`, {
    timeslot_id: timeslotId,
    sesi_id: null,
    catatan: catatan ?? null,
  })
  return res.data
}

export async function deleteDosenUnavailability(
  dosenId: string,
  unavailId: string
): Promise<void> {
  await apiClient.delete(`/dosen/${dosenId}/unavailability/${unavailId}`)
}

// ─── Preferences ──────────────────────────────────────────────────────────────

export type PreferenceFase = 'pre_schedule' | 'post_draft'

export interface DosenPreference {
  id: string
  dosen_id: string
  sesi_id: string
  timeslot_id: string
  fase: PreferenceFase
  catatan: string | null
  is_violated: boolean
  created_at: string
  // joined fields
  timeslot_label?: string
  sesi_nama?: string
}

export interface DosenPreferencePayload {
  sesi_id: string
  timeslot_id: string
  fase: PreferenceFase
  catatan?: string | null
}

export interface DosenPreferenceListParams {
  sesi_id?: string
}

export async function getDosenPreferences(
  dosenId: string,
  params?: DosenPreferenceListParams
): Promise<DosenPreference[]> {
  const res = await apiClient.get<DosenPreference[]>(`/dosen/${dosenId}/preferences`, { params })
  return res.data
}

export async function createDosenPreference(
  dosenId: string,
  data: DosenPreferencePayload
): Promise<DosenPreference> {
  const res = await apiClient.post<DosenPreference>(`/dosen/${dosenId}/preferences`, data)
  return res.data
}

export async function updateDosenPreference(
  dosenId: string,
  prefId: string,
  data: Partial<DosenPreferencePayload>
): Promise<DosenPreference> {
  const res = await apiClient.put<DosenPreference>(`/dosen/${dosenId}/preferences/${prefId}`, data)
  return res.data
}

export async function deleteDosenPreference(dosenId: string, prefId: string): Promise<void> {
  await apiClient.delete(`/dosen/${dosenId}/preferences/${prefId}`)
}
