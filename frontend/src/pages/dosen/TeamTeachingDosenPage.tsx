import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, ArrowLeftRight, Settings, AlertCircle } from 'lucide-react'

import { useAuthStore } from '@/store/authStore'
import { getSesiList, SesiJadwal } from '@/api/sesi'
import {
  getAssignments,
  getTeamTeachingOrders,
  setTeamTeachingOrder,
  swapTeamTeachingOrder,
  Assignment,
  TeamTeachingOrderItem,
} from '@/api/assignment'
import { Badge } from '@/components/Badge'
import { FormModal } from '@/components/FormModal'
import { ConfirmDialog } from '@/components/ConfirmDialog'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TeamTeachingRow {
  assignment: Assignment
  orders: TeamTeachingOrderItem[]
  isConfigured: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function checkIsConfigured(orders: TeamTeachingOrderItem[], assignment: Assignment): boolean {
  if (orders.length < 2) return false
  const d1 = orders.find((o) => o.dosen_id === assignment.dosen1_id)
  const d2 = orders.find((o) => o.dosen_id === assignment.dosen2_id)
  return !!(d1?.urutan_pra_uts && d2?.urutan_pra_uts)
}

// ─── Atur Urutan Modal ────────────────────────────────────────────────────────

interface AturUrutanModalProps {
  open: boolean
  onClose: () => void
  sesiId: string
  row: TeamTeachingRow
  myDosenId: string
}

function AturUrutanModal({ open, onClose, sesiId, row, myDosenId }: AturUrutanModalProps) {
  const queryClient = useQueryClient()
  const { assignment, orders } = row

  // Determine which dosen is "me" and which is "partner"
  const iAmDosen1 = assignment.dosen1_id === myDosenId
  const myOrder = orders.find((o) => o.dosen_id === myDosenId)

  // My urutan: 1 = masuk duluan, 2 = masuk kedua
  const [myUrutan, setMyUrutan] = useState<1 | 2>(
    (myOrder?.urutan_pra_uts as 1 | 2) ?? 1
  )
  const [catatan, setCatatan] = useState(myOrder?.catatan ?? '')
  const [error, setError] = useState<string | null>(null)

  const partnerDosen = iAmDosen1 ? assignment.dosen2 : assignment.dosen1
  const partnerUrutan: 1 | 2 = myUrutan === 1 ? 2 : 1

  const mutation = useMutation({
    mutationFn: () =>
      setTeamTeachingOrder(sesiId, assignment.id, {
        orders: [
          {
            dosen_id: myDosenId,
            urutan_pra_uts: myUrutan,
          },
          {
            dosen_id: iAmDosen1 ? assignment.dosen2_id! : assignment.dosen1_id,
            urutan_pra_uts: partnerUrutan,
          },
        ],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen-team-teaching-orders', sesiId] })
      onClose()
    },
    onError: () => setError('Gagal menyimpan urutan. Silakan coba lagi.'),
  })

  function handleSubmit() {
    setError(null)
    mutation.mutate()
  }

  return (
    <FormModal
      open={open}
      onClose={onClose}
      title="Atur Urutan Masuk Kelas (Pra-UTS)"
      onSubmit={handleSubmit}
      submitLabel="Simpan Urutan"
      loading={mutation.isPending}
      size="md"
    >
      {/* Assignment info */}
      <div className="mb-4 rounded-md bg-slate-50 px-4 py-3 text-sm">
        <div className="font-medium text-slate-800">{assignment.mk_kelas.mata_kuliah_nama}</div>
        <div className="mt-0.5 text-xs text-slate-500">
          {assignment.mk_kelas.label} · {assignment.timeslot.hari}, {assignment.timeslot.label}
        </div>
      </div>

      {error && (
        <div className="mb-3 flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
          <AlertCircle size={13} />
          {error}
        </div>
      )}

      {/* Urutan selection */}
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Urutan Masuk Kelas Saya (Pra-UTS)
        </p>

        <div className="space-y-2">
          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-slate-200 p-3 hover:bg-slate-50 has-[:checked]:border-slate-800 has-[:checked]:bg-slate-50">
            <input
              type="radio"
              name="my_urutan"
              value={1}
              checked={myUrutan === 1}
              onChange={() => setMyUrutan(1)}
              className="mt-0.5 accent-slate-800"
            />
            <div>
              <div className="text-sm font-medium text-slate-800">Saya masuk duluan (Urutan 1)</div>
              <div className="text-xs text-slate-500">
                {partnerDosen?.nama ?? 'Rekan'} masuk kedua (Urutan 2)
              </div>
            </div>
          </label>

          <label className="flex cursor-pointer items-start gap-3 rounded-md border border-slate-200 p-3 hover:bg-slate-50 has-[:checked]:border-slate-800 has-[:checked]:bg-slate-50">
            <input
              type="radio"
              name="my_urutan"
              value={2}
              checked={myUrutan === 2}
              onChange={() => setMyUrutan(2)}
              className="mt-0.5 accent-slate-800"
            />
            <div>
              <div className="text-sm font-medium text-slate-800">Rekan saya masuk duluan (Urutan 2)</div>
              <div className="text-xs text-slate-500">
                {partnerDosen?.nama ?? 'Rekan'} masuk duluan (Urutan 1), saya masuk kedua
              </div>
            </div>
          </label>
        </div>

        {/* Catatan */}
        <div className="mt-3">
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Catatan (opsional)
          </label>
          <textarea
            value={catatan}
            onChange={(e) => setCatatan(e.target.value)}
            rows={2}
            placeholder="Tambahkan catatan jika diperlukan..."
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
          />
        </div>
      </div>
    </FormModal>
  )
}

// ─── Swap Pasca-UTS Confirm ───────────────────────────────────────────────────

interface SwapConfirmProps {
  open: boolean
  onClose: () => void
  sesiId: string
  row: TeamTeachingRow
  myDosenId: string
}

function SwapPascaUTSConfirm({ open, onClose, sesiId, row, myDosenId }: SwapConfirmProps) {
  const queryClient = useQueryClient()
  const { assignment, orders } = row

  const iAmDosen1 = assignment.dosen1_id === myDosenId
  const myOrder = orders.find((o) => o.dosen_id === myDosenId)

  // Swap: invert the pra-UTS urutan for pasca-UTS
  const myPraUrutan = myOrder?.urutan_pra_uts ?? 1
  const myPascaUrutan: 1 | 2 = myPraUrutan === 1 ? 2 : 1
  const partnerPascaUrutan: 1 | 2 = myPascaUrutan === 1 ? 2 : 1

  const mutation = useMutation({
    mutationFn: () =>
      swapTeamTeachingOrder(sesiId, assignment.id, {
        orders: [
          { dosen_id: myDosenId, urutan_pasca_uts: myPascaUrutan },
          {
            dosen_id: iAmDosen1 ? assignment.dosen2_id! : assignment.dosen1_id,
            urutan_pasca_uts: partnerPascaUrutan,
          },
        ],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen-team-teaching-orders', sesiId] })
      onClose()
    },
  })

  const partnerDosen = iAmDosen1 ? assignment.dosen2 : assignment.dosen1

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={() => mutation.mutate()}
      title="Konfirmasi Swap Pasca-UTS"
      message={`Urutan masuk kelas akan dipertukarkan setelah UTS untuk MK ${assignment.mk_kelas.mata_kuliah_nama} (${assignment.mk_kelas.label}). Anda dan ${partnerDosen?.nama ?? 'rekan'} akan bertukar urutan. Lanjutkan?`}
      confirmLabel="Ya, Swap Sekarang"
      cancelLabel="Batal"
      variant="warning"
      loading={mutation.isPending}
    />
  )
}

// ─── Row Card ─────────────────────────────────────────────────────────────────

interface RowCardProps {
  row: TeamTeachingRow
  myDosenId: string
  onAturUrutan: (row: TeamTeachingRow) => void
  onSwap: (row: TeamTeachingRow) => void
}

function TeamTeachingRowCard({ row, myDosenId, onAturUrutan, onSwap }: RowCardProps) {
  const { assignment, orders, isConfigured } = row
  const iAmDosen1 = assignment.dosen1_id === myDosenId
  const partnerDosen = iAmDosen1 ? assignment.dosen2 : assignment.dosen1
  const myOrder = orders.find((o) => o.dosen_id === myDosenId)
  const hasSwapped = myOrder?.urutan_pasca_uts != null

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        {/* MK info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-800">
              {assignment.mk_kelas.mata_kuliah_nama}
            </span>
            <span className="text-xs text-slate-400">{assignment.mk_kelas.label}</span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-slate-500 flex-wrap">
            <span>{assignment.timeslot.hari}, {assignment.timeslot.label}</span>
            {assignment.ruang && <span>· {assignment.ruang.nama}</span>}
            <span>· {assignment.mk_kelas.sks} SKS</span>
          </div>

          {/* Partner info */}
          <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-600">
            <Users size={12} className="text-slate-400" />
            <span>Rekan: <span className="font-medium">{partnerDosen?.nama ?? '—'}</span></span>
          </div>

          {/* Urutan info */}
          {isConfigured && myOrder && (
            <div className="mt-2 flex items-center gap-3 text-xs flex-wrap">
              <span className="text-slate-500">
                Pra-UTS: <span className="font-medium text-slate-700">Urutan {myOrder.urutan_pra_uts}</span>
              </span>
              {hasSwapped && (
                <span className="text-slate-500">
                  Pasca-UTS: <span className="font-medium text-slate-700">Urutan {myOrder.urutan_pasca_uts}</span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Status + Actions */}
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <Badge variant={isConfigured ? 'success' : 'default'}>
            {isConfigured ? 'Sudah Diatur' : 'Belum Diatur'}
          </Badge>
          {hasSwapped && (
            <Badge variant="info">Swap Terjadwal</Badge>
          )}

          <div className="flex items-center gap-1.5 mt-1">
            <button
              type="button"
              onClick={() => onAturUrutan(row)}
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Settings size={12} />
              Atur Urutan
            </button>
            <button
              type="button"
              onClick={() => onSwap(row)}
              disabled={!isConfigured}
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title={!isConfigured ? 'Atur urutan pra-UTS terlebih dahulu' : 'Jadwalkan pertukaran pasca-UTS'}
            >
              <ArrowLeftRight size={12} />
              Swap Pasca-UTS
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TeamTeachingDosenPage() {
  const { user } = useAuthStore()
  const [selectedSesiId, setSelectedSesiId] = useState<string>('')
  const [atuRowModal, setAturRowModal] = useState<TeamTeachingRow | null>(null)
  const [swapRow, setSwapRow] = useState<TeamTeachingRow | null>(null)

  // ── Fetch sesi list ────────────────────────────────────────────────────────

  const { data: sesiList = [], isLoading: sesiLoading } = useQuery({
    queryKey: ['sesi'],
    queryFn: getSesiList,
    select: (data: SesiJadwal[]) =>
      data.filter((s) => s.status === 'Aktif' || s.status === 'Draft'),
  })

  const effectiveSesiId = selectedSesiId || sesiList[0]?.id || ''
  const selectedSesi = sesiList.find((s) => s.id === effectiveSesiId)

  // ── Fetch assignments (backend filters to dosen's own) ─────────────────────

  const {
    data: assignmentData,
    isLoading: assignmentsLoading,
    isError,
  } = useQuery({
    queryKey: ['dosen-assignments', effectiveSesiId],
    queryFn: () => getAssignments(effectiveSesiId, { page: 1, page_size: 200 }),
    enabled: !!effectiveSesiId,
  })

  // Filter to team teaching only (dosen2_id not null)
  const teamTeachingAssignments = (assignmentData?.items ?? []).filter(
    (a) => a.dosen2_id !== null
  )

  // ── Fetch team teaching orders for each assignment ─────────────────────────

  const { data: ordersMap, isLoading: ordersLoading } = useQuery({
    queryKey: ['dosen-team-teaching-orders', effectiveSesiId, teamTeachingAssignments.map((a) => a.id)],
    queryFn: async () => {
      const results: Record<string, TeamTeachingOrderItem[]> = {}
      await Promise.all(
        teamTeachingAssignments.map(async (a) => {
          try {
            const res = await getTeamTeachingOrders(effectiveSesiId, a.id)
            results[a.id] = res.items
          } catch {
            results[a.id] = []
          }
        })
      )
      return results
    },
    enabled: !!effectiveSesiId && teamTeachingAssignments.length > 0,
  })

  const isLoading = sesiLoading || assignmentsLoading || ordersLoading

  // ── Resolve my dosen ID ────────────────────────────────────────────────────
  // For dosen role, assignments returned are their own — pick dosen1_id or dosen2_id
  // that matches the current user's linked dosen. We infer from the first assignment.
  function resolveMyDosenId(assignments: Assignment[]): string | null {
    if (!user) return null
    // The backend returns assignments where the dosen is dosen1 or dosen2.
    // We can't directly match user.id → dosen.id without an extra API call.
    // Use the first assignment to figure out which slot is "me" by checking
    // if dosen1 or dosen2 appears consistently across assignments.
    // Since all assignments belong to this dosen, dosen1_id or dosen2_id will be consistent.
    const ids = new Map<string, number>()
    for (const a of assignments) {
      ids.set(a.dosen1_id, (ids.get(a.dosen1_id) ?? 0) + 1)
      if (a.dosen2_id) ids.set(a.dosen2_id, (ids.get(a.dosen2_id) ?? 0) + 1)
    }
    // The dosen ID that appears most frequently is likely "me"
    let maxCount = 0
    let myId: string | null = null
    for (const [id, count] of ids.entries()) {
      if (count > maxCount) {
        maxCount = count
        myId = id
      }
    }
    return myId
  }

  const allAssignments = assignmentData?.items ?? []
  const myDosenId = resolveMyDosenId(allAssignments)

  // ── Build rows ─────────────────────────────────────────────────────────────

  const rows: TeamTeachingRow[] = teamTeachingAssignments.map((a) => {
    const orders = ordersMap?.[a.id] ?? []
    return {
      assignment: a,
      orders,
      isConfigured: checkIsConfigured(orders, a),
    }
  })

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Users size={18} className="text-slate-500" />
          <div>
            <h1 className="text-base font-semibold text-slate-900">Team Teaching</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Atur urutan masuk kelas untuk mata kuliah yang diampu bersama
            </p>
          </div>
        </div>

        {/* Sesi selector */}
        {sesiList.length > 1 && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-500">Sesi:</label>
            <select
              value={effectiveSesiId}
              onChange={(e) => setSelectedSesiId(e.target.value)}
              disabled={sesiLoading}
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:opacity-50"
            >
              {sesiList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nama} ({s.semester} {s.tahun_akademik})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Sesi badge */}
      {selectedSesi && (
        <div className="text-xs text-slate-500">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                selectedSesi.status === 'Aktif' ? 'bg-green-500' : 'bg-yellow-400'
              }`}
            />
            {selectedSesi.status} · {selectedSesi.semester} {selectedSesi.tahun_akademik}
          </span>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={15} />
          Gagal memuat data. Silakan coba lagi.
        </div>
      )}

      {/* No sesi */}
      {!sesiLoading && sesiList.length === 0 && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-6 py-10 text-center">
          <Users size={32} className="mx-auto mb-2 text-slate-300" />
          <p className="text-sm text-slate-500">Tidak ada sesi jadwal aktif saat ini.</p>
        </div>
      )}

      {/* Loading */}
      {isLoading && effectiveSesiId && (
        <div className="flex items-center justify-center py-16 text-sm text-slate-400">
          Memuat data team teaching…
        </div>
      )}

      {/* Empty state — no team teaching assignments */}
      {!isLoading && !isError && effectiveSesiId && rows.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-6 py-12 text-center">
          <Users size={36} className="mx-auto mb-3 text-slate-300" />
          <p className="text-sm font-medium text-slate-600">Tidak ada mata kuliah team teaching</p>
          <p className="mt-1 text-xs text-slate-400">
            Anda tidak memiliki assignment team teaching pada sesi ini.
            Team teaching aktif jika ada dosen kedua yang ditugaskan pada mata kuliah yang sama.
          </p>
        </div>
      )}

      {/* Team teaching list */}
      {!isLoading && rows.length > 0 && myDosenId && (
        <div className="space-y-3">
          {/* Summary */}
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span>{rows.length} mata kuliah team teaching</span>
            <span>·</span>
            <span>{rows.filter((r) => r.isConfigured).length} sudah dikonfigurasi</span>
          </div>

          {rows.map((row) => (
            <TeamTeachingRowCard
              key={row.assignment.id}
              row={row}
              myDosenId={myDosenId}
              onAturUrutan={setAturRowModal}
              onSwap={setSwapRow}
            />
          ))}
        </div>
      )}

      {/* Atur Urutan Modal */}
      {atuRowModal && effectiveSesiId && myDosenId && (
        <AturUrutanModal
          open={!!atuRowModal}
          onClose={() => setAturRowModal(null)}
          sesiId={effectiveSesiId}
          row={atuRowModal}
          myDosenId={myDosenId}
        />
      )}

      {/* Swap Pasca-UTS Confirm */}
      {swapRow && effectiveSesiId && myDosenId && (
        <SwapPascaUTSConfirm
          open={!!swapRow}
          onClose={() => setSwapRow(null)}
          sesiId={effectiveSesiId}
          row={swapRow}
          myDosenId={myDosenId}
        />
      )}
    </div>
  )
}
