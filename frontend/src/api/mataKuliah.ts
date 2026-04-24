import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface KurikulumNested {
  id: string
  kode: string
  tahun: string
  prodi_id: string
}

export interface MataKuliah {
  id: string
  kode: string
  kurikulum_id: string
  nama: string
  sks: number
  semester: number
  jenis: string
  prasyarat: string | null
  is_active: boolean
  created_at: string
  kurikulum: KurikulumNested | null
}

export interface MataKuliahCreatePayload {
  kode: string
  kurikulum_id: string
  nama: string
  sks: number
  semester: number
  jenis: string
  prasyarat: string | null
}

export interface MataKuliahKelas {
  id: string
  mata_kuliah_id: string
  kelas: string | null
  label: string
  ket: string | null
  created_at: string
}

export interface MataKuliahKelasPayload {
  kelas: string | null
  label: string
  ket: string | null
}

export interface Kurikulum {
  id: string
  kode: string
  tahun: string
  prodi_id: string
  is_active: boolean
}

// ─── Mata Kuliah API ──────────────────────────────────────────────────────────

export interface MataKuliahFilter {
  prodi_id?: string
  kurikulum_id?: string
  semester?: number
}

export async function getMataKuliah(filters?: MataKuliahFilter): Promise<MataKuliah[]> {
  const params: Record<string, string | number> = {}
  if (filters?.prodi_id) params.prodi_id = filters.prodi_id
  if (filters?.kurikulum_id) params.kurikulum_id = filters.kurikulum_id
  if (filters?.semester !== undefined) params.semester = filters.semester
  const res = await apiClient.get<MataKuliah[]>('/mata-kuliah', { params })
  return res.data
}

export async function createMataKuliah(data: MataKuliahCreatePayload): Promise<MataKuliah> {
  const res = await apiClient.post<MataKuliah>('/mata-kuliah', data)
  return res.data
}

export async function updateMataKuliah(
  id: string,
  data: Partial<MataKuliahCreatePayload>
): Promise<MataKuliah> {
  const res = await apiClient.put<MataKuliah>(`/mata-kuliah/${id}`, data)
  return res.data
}

export async function deleteMataKuliah(id: string): Promise<void> {
  await apiClient.delete(`/mata-kuliah/${id}`)
}

// ─── Kelas API ────────────────────────────────────────────────────────────────

export async function getKelas(mkId: string): Promise<MataKuliahKelas[]> {
  const res = await apiClient.get<MataKuliahKelas[]>(`/mata-kuliah/${mkId}/kelas`)
  return res.data
}

export async function createKelas(
  mkId: string,
  data: MataKuliahKelasPayload
): Promise<MataKuliahKelas> {
  const res = await apiClient.post<MataKuliahKelas>(`/mata-kuliah/${mkId}/kelas`, data)
  return res.data
}

export async function updateKelas(
  mkId: string,
  kelasId: string,
  data: Partial<MataKuliahKelasPayload>
): Promise<MataKuliahKelas> {
  const res = await apiClient.put<MataKuliahKelas>(
    `/mata-kuliah/${mkId}/kelas/${kelasId}`,
    data
  )
  return res.data
}

export async function deleteKelas(mkId: string, kelasId: string): Promise<void> {
  await apiClient.delete(`/mata-kuliah/${mkId}/kelas/${kelasId}`)
}

// ─── Kurikulum API ────────────────────────────────────────────────────────────

export async function getKurikulum(): Promise<Kurikulum[]> {
  const res = await apiClient.get<Kurikulum[]>('/kurikulum')
  return res.data
}
