import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ProdiInfo {
  id: string
  kode: string
  nama: string
  singkat: string
}

export interface TimeslotInfo {
  id: string
  kode: string
  hari: string
  sesi: number
  jam_mulai: string
  jam_selesai: string
  label: string
}

export interface RuangInfo {
  id: string
  nama: string
  kapasitas: number
  lantai: number | null
  gedung: string | null
}

export interface DosenInfo {
  id: string
  kode: string
  nama: string
}

export interface MkKelasInfo {
  id: string
  label: string
  kelas: string | null
  mata_kuliah_kode: string
  mata_kuliah_nama: string
  semester: number
  sks: number
  prodi: ProdiInfo
}

export interface Assignment {
  id: string
  sesi_id: string
  mk_kelas_id: string
  dosen1_id: string
  dosen2_id: string | null
  timeslot_id: string
  ruang_id: string | null
  override_floor_priority: boolean
  catatan: string | null
  created_at: string
  updated_at: string
  mk_kelas: MkKelasInfo
  dosen1: DosenInfo
  dosen2: DosenInfo | null
  timeslot: TimeslotInfo
  ruang: RuangInfo | null
}

export interface AssignmentListResponse {
  items: Assignment[]
  total: number
  page: number
  page_size: number
}

export interface AssignmentListParams {
  prodi_id?: string
  hari?: string
  semester?: number
  page?: number
  page_size?: number
}

export interface AssignmentCreatePayload {
  mk_kelas_id: string
  dosen1_id: string
  dosen2_id?: string | null
  timeslot_id: string
  ruang_id?: string | null
  catatan?: string | null
}

export interface AssignmentUpdatePayload {
  mk_kelas_id: string
  dosen1_id: string
  dosen2_id?: string | null
  timeslot_id: string
  ruang_id?: string | null
  catatan?: string | null
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getAssignments(
  sesiId: string,
  params?: AssignmentListParams
): Promise<AssignmentListResponse> {
  const res = await apiClient.get<AssignmentListResponse>(
    `/sesi/${sesiId}/assignments`,
    { params }
  )
  return res.data
}

export async function createAssignment(
  sesiId: string,
  data: AssignmentCreatePayload
): Promise<Assignment> {
  const res = await apiClient.post<Assignment>(`/sesi/${sesiId}/assignments`, data)
  return res.data
}

export async function updateAssignment(
  sesiId: string,
  assignmentId: string,
  data: AssignmentUpdatePayload
): Promise<Assignment> {
  const res = await apiClient.put<Assignment>(
    `/sesi/${sesiId}/assignments/${assignmentId}`,
    data
  )
  return res.data
}

export async function overrideFloorPriority(
  sesiId: string,
  assignmentId: string
): Promise<Assignment> {
  const res = await apiClient.patch<Assignment>(
    `/sesi/${sesiId}/assignments/${assignmentId}/override-floor`
  )
  return res.data
}

// ─── Team Teaching Types ──────────────────────────────────────────────────────

export interface TeamTeachingOrderItem {
  id: string
  assignment_id: string
  dosen_id: string
  urutan_pra_uts: number
  urutan_pasca_uts: number | null
  catatan: string | null
}

export interface TeamTeachingResponse {
  items: TeamTeachingOrderItem[]
}

export interface TeamTeachingSetItem {
  dosen_id: string
  urutan_pra_uts: number
}

export interface TeamTeachingSetRequest {
  orders: TeamTeachingSetItem[]
}

export interface TeamTeachingSwapItem {
  dosen_id: string
  urutan_pasca_uts: number
}

export interface TeamTeachingSwapRequest {
  orders: TeamTeachingSwapItem[]
}

// ─── Team Teaching API Functions ──────────────────────────────────────────────

export async function getTeamTeachingOrders(
  sesiId: string,
  assignmentId: string
): Promise<TeamTeachingResponse> {
  const res = await apiClient.get<TeamTeachingResponse>(
    `/sesi/${sesiId}/assignments/${assignmentId}/team-teaching`
  )
  return res.data
}

export async function setTeamTeachingOrder(
  sesiId: string,
  assignmentId: string,
  data: TeamTeachingSetRequest
): Promise<TeamTeachingResponse> {
  const res = await apiClient.put<TeamTeachingResponse>(
    `/sesi/${sesiId}/assignments/${assignmentId}/team-teaching`,
    data
  )
  return res.data
}

export async function swapTeamTeachingOrder(
  sesiId: string,
  assignmentId: string,
  data: TeamTeachingSwapRequest
): Promise<TeamTeachingResponse> {
  const res = await apiClient.post<TeamTeachingResponse>(
    `/sesi/${sesiId}/assignments/${assignmentId}/team-teaching/swap`,
    data
  )
  return res.data
}
