import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ImportWarning {
  row: number
  sheet: string
  value: string
  reason: string
}

export interface ImportResult {
  total: number
  inserted: number
  updated: number
  skipped: number
  warnings: ImportWarning[]
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function importMaster(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post<ImportResult>('/import/master', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function importJadwal(file: File, sesi_id: string): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post<ImportResult>(`/import/jadwal?sesi_id=${sesi_id}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function exportJadwal(sesiId: string, sesiNama?: string): Promise<void> {
  const res = await apiClient.get(`/sesi/${sesiId}/export`, {
    responseType: 'blob',
  })
  
  const blob = new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = sesiNama ? `jadwal-${sesiNama}.xlsx` : 'jadwal-export.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
