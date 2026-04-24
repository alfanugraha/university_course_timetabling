import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Pencil } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { Badge } from '@/components/Badge'
import { FormModal } from '@/components/FormModal'
import { useAuthStore } from '@/store/authStore'

import { getSesiList } from '@/api/sesi'
import {
  getAssignments,
  getTeamTeachingOrders,
  setTeamTeachingOrder,
  swapTeamTeachingOrder,
  Assignment,
  TeamTeachingOrderItem,
} from '@/api/assignment'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TeamTeachingRow {
  id: string
  assignment: Assignment
  orders: TeamTeachingOrderItem[]
  isConfigured: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isConfigured(orders: TeamTeachingOrderItem[], assignment: Assignment): boolean {
  if (orders.length < 2) return false
  const d1Order = orders.find((o) => o.dosen_id === assignment.dosen1_id)
  const d2Order = orders.find((o) => o.dosen_id === assignment.dosen2_id)
  return !!(d1Order?.urutan_pra_uts && d2Order?.urutan_pra_uts)
}

// ─── Team Teaching Order Modal ────────────────────────────────────────────────

interface OrderModalProps {
  open: boolean
  onClose: () => void
  sesiId: string
  assignment: Assignment
  orders: TeamTeachingOrderItem[]
}

function TeamTeachingOrderModal({ open, onClose, sesiId, assignment, orders }: OrderModalProps) {
  const queryClient = useQueryClient()

  const d1Order = orders.find((o) => o.dosen_id === assignment.dosen1_id)
  const d2Order = orders.find((o) => o.dosen_id === assignment.dosen2_id)

  const [d1Urutan, setD1Urutan] = useState<number>(d1Order?.urutan_pra_uts ?? 1)
  const [d2Urutan, setD2Urutan] = useState<number>(d2Order?.urutan_pra_uts ?? 2)

  const [d1UrutanPasca, setD1UrutanPasca] = useState<number>(d1Order?.urutan_pasca_uts ?? 2)
  const [d2UrutanPasca, setD2UrutanPasca] = useState<number>(d2Order?.urutan_pasca_uts ?? 1)

  const [showSwap, setShowSwap] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setMutation = useMutation({
    mutationFn: () =>
      setTeamTeachingOrder(sesiId, assignment.id, {
        orders: [
          { dosen_id: assignment.dosen1_id, urutan_pra_uts: d1Urutan },
          { dosen_id: assignment.dosen2_id!, urutan_pra_uts: d2Urutan },
        ],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-teaching-orders', sesiId] })
      onClose()
    },
    onError: () => setError('Gagal menyimpan urutan. Silakan coba lagi.'),
  })

  const swapMutation = useMutation({
    mutationFn: () =>
      swapTeamTeachingOrder(sesiId, assignment.id, {
        orders: [
          { dosen_id: assignment.dosen1_id, urutan_pasca_uts: d1UrutanPasca },
          { dosen_id: assignment.dosen2_id!, urutan_pasca_uts: d2UrutanPasca },
        ],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-teaching-orders', sesiId] })
      setShowSwap(false)
    },
    onError: () => setError('Gagal menyimpan pertukaran. Silakan coba lagi.'),
  })

  function handleSubmit() {
    if (d1Urutan === d2Urutan) {
      setError('Urutan pra-UTS kedua dosen tidak boleh sama.')
      return
    }
    setError(null)
    setMutation.mutate()
  }

  return (
    <FormModal
      open={open}
      onClose={onClose}
      title="Atur Urutan Team Teaching"
      onSubmit={handleSubmit}
      submitLabel="Simpan Urutan Pra-UTS"
      loading={setMutation.isPending}
      size="md"
    >
      {/* Assignment info */}
      <div className="mb-4 rounded-md bg-slate-50 px-4 py-3 text-sm">
        <div className="font-medium text-slate-800">{assignment.mk_kelas.mata_kuliah_nama}</div>
        <div className="mt-0.5 text-xs text-slate-500">
          {assignment.mk_kelas.label} · Semester {assignment.mk_kelas.semester}
        </div>
      </div>

      {error && (
        <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
      )}

      {/* Pra-UTS urutan */}
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Urutan Masuk Kelas (Pra-UTS)
        </p>

        <div className="flex items-center justify-between gap-4">
          <span className="text-sm text-slate-700">{assignment.dosen1.nama}</span>
          <div className="flex gap-3">
            {[1, 2].map((n) => (
              <label key={n} className="flex cursor-pointer items-center gap-1.5 text-sm">
                <input
                  type="radio"
                  name="d1_urutan"
                  value={n}
                  checked={d1Urutan === n}
                  onChange={() => setD1Urutan(n)}
                  className="accent-slate-800"
                />
                {n === 1 ? 'Masuk Duluan' : 'Masuk Kedua'}
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="text-sm text-slate-700">{assignment.dosen2?.nama}</span>
          <div className="flex gap-3">
            {[1, 2].map((n) => (
              <label key={n} className="flex cursor-pointer items-center gap-1.5 text-sm">
                <input
                  type="radio"
                  name="d2_urutan"
                  value={n}
                  checked={d2Urutan === n}
                  onChange={() => setD2Urutan(n)}
                  className="accent-slate-800"
                />
                {n === 1 ? 'Masuk Duluan' : 'Masuk Kedua'}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Pasca-UTS swap section */}
      <div className="mt-5 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => setShowSwap((v) => !v)}
          className="text-xs font-medium text-slate-500 underline hover:text-slate-800"
        >
          {showSwap ? 'Sembunyikan' : 'Atur Pertukaran Pasca-UTS'}
        </button>

        {showSwap && (
          <div className="mt-3 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Urutan Masuk Kelas (Pasca-UTS)
            </p>

            <div className="flex items-center justify-between gap-4">
              <span className="text-sm text-slate-700">{assignment.dosen1.nama}</span>
              <div className="flex gap-3">
                {[1, 2].map((n) => (
                  <label key={n} className="flex cursor-pointer items-center gap-1.5 text-sm">
                    <input
                      type="radio"
                      name="d1_pasca"
                      value={n}
                      checked={d1UrutanPasca === n}
                      onChange={() => setD1UrutanPasca(n)}
                      className="accent-slate-800"
                    />
                    {n === 1 ? 'Masuk Duluan' : 'Masuk Kedua'}
                  </label>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between gap-4">
              <span className="text-sm text-slate-700">{assignment.dosen2?.nama}</span>
              <div className="flex gap-3">
                {[1, 2].map((n) => (
                  <label key={n} className="flex cursor-pointer items-center gap-1.5 text-sm">
                    <input
                      type="radio"
                      name="d2_pasca"
                      value={n}
                      checked={d2UrutanPasca === n}
                      onChange={() => setD2UrutanPasca(n)}
                      className="accent-slate-800"
                    />
                    {n === 1 ? 'Masuk Duluan' : 'Masuk Kedua'}
                  </label>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={() => swapMutation.mutate()}
              disabled={swapMutation.isPending}
              className="mt-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {swapMutation.isPending ? 'Menyimpan...' : 'Simpan Pertukaran Pasca-UTS'}
            </button>
          </div>
        )}
      </div>
    </FormModal>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TeamTeachingPage() {
  const { id: sesiId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isDosen = user?.role === 'dosen'

  const [editingRow, setEditingRow] = useState<TeamTeachingRow | null>(null)

  // ── Fetch sesi info ────────────────────────────────────────────────────────

  const { data: sesiList = [] } = useQuery({
    queryKey: ['sesi'],
    queryFn: getSesiList,
  })
  const sesi = sesiList.find((s) => s.id === sesiId)

  // ── Fetch all assignments (large page to get all) ──────────────────────────

  const {
    data: assignmentData,
    isLoading: loadingAssignments,
    isError,
  } = useQuery({
    queryKey: ['assignments', sesiId, { page_size: 500 }],
    queryFn: () => getAssignments(sesiId!, { page: 1, page_size: 500 }),
    enabled: !!sesiId,
  })

  // Filter to team teaching only (dosen2 not null)
  const teamTeachingAssignments = (assignmentData?.items ?? []).filter((a) => a.dosen2 !== null)

  // ── Fetch team teaching orders for each assignment ─────────────────────────

  const {
    data: ordersMap,
    isLoading: loadingOrders,
  } = useQuery({
    queryKey: ['team-teaching-orders', sesiId, teamTeachingAssignments.map((a) => a.id)],
    queryFn: async () => {
      const results: Record<string, TeamTeachingOrderItem[]> = {}
      await Promise.all(
        teamTeachingAssignments.map(async (a) => {
          try {
            const res = await getTeamTeachingOrders(sesiId!, a.id)
            results[a.id] = res.items
          } catch {
            results[a.id] = []
          }
        })
      )
      return results
    },
    enabled: !!sesiId && teamTeachingAssignments.length > 0,
  })

  const isLoading = loadingAssignments || loadingOrders

  // ── Build rows ─────────────────────────────────────────────────────────────

  const rows: TeamTeachingRow[] = teamTeachingAssignments.map((a) => {
    const orders = ordersMap?.[a.id] ?? []
    return {
      id: a.id,
      assignment: a,
      orders,
      isConfigured: isConfigured(orders, a),
    }
  })

  // ── RBAC: can dosen edit this row? ─────────────────────────────────────────

  function canDosenEdit(row: TeamTeachingRow): boolean {
    if (!isDosen || !user) return false
    // We need to check if user's dosen record matches dosen1 or dosen2
    // The backend filters assignments to only show dosen's own, so all rows are editable
    // But we double-check via dosen1_id / dosen2_id matching user's linked dosen
    // Since we don't have dosen.id in authStore, we rely on backend filtering:
    // for dosen role, getAssignments already returns only their own assignments
    return true
  }

  // ── Columns ────────────────────────────────────────────────────────────────

  const columns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: 'mk_kelas_nama',
      label: 'Mata Kuliah',
      sortable: true,
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        return (
          <div>
            <div className="text-sm font-medium text-slate-800">
              {r.assignment.mk_kelas.mata_kuliah_nama}
            </div>
            <div className="text-[10px] text-slate-400">{r.assignment.mk_kelas.label}</div>
          </div>
        )
      },
    },
    {
      key: 'semester',
      label: 'Smt',
      sortable: true,
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        return <span className="text-xs text-slate-600">{r.assignment.mk_kelas.semester}</span>
      },
    },
    {
      key: 'dosen1',
      label: 'Dosen I',
      sortable: true,
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        const order = r.orders.find((o) => o.dosen_id === r.assignment.dosen1_id)
        return (
          <div>
            <div className="text-xs text-slate-700">{r.assignment.dosen1.nama}</div>
            {order && (
              <div className="text-[10px] text-slate-400">
                Pra-UTS: urutan {order.urutan_pra_uts}
                {order.urutan_pasca_uts != null && ` · Pasca-UTS: urutan ${order.urutan_pasca_uts}`}
              </div>
            )}
          </div>
        )
      },
    },
    {
      key: 'dosen2',
      label: 'Dosen II',
      sortable: true,
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        const order = r.orders.find((o) => o.dosen_id === r.assignment.dosen2_id)
        return (
          <div>
            <div className="text-xs text-slate-700">{r.assignment.dosen2?.nama}</div>
            {order && (
              <div className="text-[10px] text-slate-400">
                Pra-UTS: urutan {order.urutan_pra_uts}
                {order.urutan_pasca_uts != null && ` · Pasca-UTS: urutan ${order.urutan_pasca_uts}`}
              </div>
            )}
          </div>
        )
      },
    },
    {
      key: 'timeslot',
      label: 'Waktu',
      sortable: true,
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        return (
          <span className="text-xs text-slate-600">
            {r.assignment.timeslot.hari}, {r.assignment.timeslot.label}
          </span>
        )
      },
    },
    {
      key: 'ruang',
      label: 'Ruang',
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        return r.assignment.ruang ? (
          <span className="text-xs text-slate-600">{r.assignment.ruang.nama}</span>
        ) : (
          <span className="text-xs text-slate-300">—</span>
        )
      },
    },
    {
      key: 'status',
      label: 'Status Konfigurasi',
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        return r.isConfigured ? (
          <Badge variant="success">Sudah Diatur</Badge>
        ) : (
          <Badge variant="default">Belum Diatur</Badge>
        )
      },
    },
  ]

  // Add action column only for dosen role
  if (isDosen) {
    columns.push({
      key: '_actions',
      label: '',
      render: (_val, row) => {
        const r = row as unknown as TeamTeachingRow
        if (!canDosenEdit(r)) return null
        return (
          <button
            type="button"
            onClick={() => setEditingRow(r)}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Atur urutan team teaching"
          >
            <Pencil size={13} />
          </button>
        )
      },
    })
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/sesi/${sesiId}`)}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Kembali"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-base font-semibold text-slate-900">Team Teaching</h1>
            {sesi && (
              <div className="mt-0.5 text-xs text-slate-500">
                {sesi.nama} · {sesi.semester} {sesi.tahun_akademik}
              </div>
            )}
          </div>
        </div>

        {!isLoading && (
          <div className="text-right">
            <div className="text-lg font-semibold text-slate-800">{rows.length}</div>
            <div className="text-[10px] text-slate-400">assignment team teaching</div>
          </div>
        )}
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={rows as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Tidak ada assignment team teaching dalam sesi ini."
      />

      {/* Edit Modal (dosen only) */}
      {editingRow && sesiId && (
        <TeamTeachingOrderModal
          open={!!editingRow}
          onClose={() => setEditingRow(null)}
          sesiId={sesiId}
          assignment={editingRow.assignment}
          orders={editingRow.orders}
        />
      )}
    </div>
  )
}
