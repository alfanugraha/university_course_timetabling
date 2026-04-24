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
