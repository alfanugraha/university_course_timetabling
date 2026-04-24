import apiClient from './client'

export interface Prodi {
  id: string
  kode: string
  strata: string
  nama: string
  singkat: string
  kategori: string
  is_active: boolean
}

export interface ProdiCreatePayload {
  kode: string
  strata: string
  nama: string
  singkat: string
  kategori: string
  is_active: boolean
}

export async function getProdi(): Promise<Prodi[]> {
  const res = await apiClient.get<Prodi[]>('/prodi')
  return res.data
}

export async function createProdi(data: ProdiCreatePayload): Promise<Prodi> {
  const res = await apiClient.post<Prodi>('/prodi', data)
  return res.data
}

export async function updateProdi(id: string, data: Partial<ProdiCreatePayload>): Promise<Prodi> {
  const res = await apiClient.put<Prodi>(`/prodi/${id}`, data)
  return res.data
}
