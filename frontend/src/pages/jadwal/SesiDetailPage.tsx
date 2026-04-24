import { useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Filter, X, Plus, Pencil, Users, AlertCircle, AlertTriangle, ShieldAlert, Download } from 'lucide-react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { Badge } from '@/components/Badge'
import { AddAssignmentModal } from '@/components/AddAssignmentModal'
import { EditAssignmentModal } from '@/components/EditAssignmentModal'
import { useAuthStore } from '@/store/authStore'

import { getSesiList, SesiJadwal } from '@/api/sesi'
import { getAssignments, Assignment, AssignmentListParams } from '@/api/assignment'
import { getProdi, Prodi } from '@/api/prodi'
import { getConflicts, ConflictLog } from '@/api/conflict'
import { exportJadwal } from '@/api/importExport'

// ─── RBAC ─────────────────────────────────────────────────────────────────────

const EDITOR_ROLES_PRODI = [
  'admin',
  'sekretaris_jurusan',
  'tendik_jurusan',
  'koordinator_prodi',
  'tendik_prodi',
]

const EXPORT_ROLES = [
  'admin',
  'sekretaris_jurusan',
  'tendik_jurusan',
  'koordinator_prodi',
  'tendik_prodi',
  'ketua_jurusan',
]

// ─── Constants ────────────────────────────────────────────────────────────────

const HARI_OPTIONS = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat']
const SEMESTER_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8]
const PAGE_SIZE = 20

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(t: string): string {
  return t.slice(0, 5)
}

// Build a map of assignment_id → ConflictLog[] from the conflict list
function buildConflictMap(conflicts: ConflictLog[]): Map<string, ConflictLog[]> {
  const map = new Map<string, ConflictLog[]>()
  for (const c of conflicts) {
    for (const aid of c.assignment_ids) {
      const existing = map.get(aid) ?? []
      existing.push(c)
      map.set(aid, existing)
    }
  }
  return map
}

// Determine the highest severity for a set of conflicts
function topSeverity(conflicts: ConflictLog[]): 'ERROR' | 'WARNING' | null {
  if (conflicts.some((c) => c.severity === 'ERROR')) return 'ERROR'
  if (conflicts.some((c) => c.severity === 'WARNING')) return 'WARNING'
  return null
}

// ─── Conflict Tooltip ─────────────────────────────────────────────────────────

function ConflictIndicator({ conflicts }: { conflicts: ConflictLog[] }) {
  const severity = topSeverity(conflicts)
  if (!severity) return null

  const isError = severity === 'ERROR'
  const Icon = isError ? AlertCircle : AlertTriangle
  const iconClass = isError
    ? 'text-red-500 hover:text-red-700'
    : 'text-yellow-500 hover:text-yellow-700'

  const messages = conflicts.map((c) => c.pesan)

  return (
    <TooltipPrimitive.Provider delayDuration={200}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>
          <button
            type="button"
            className={`inline-flex items-center rounded p-0.5 ${iconClass} focus:outline-none`}
            aria-label={`Konflik: ${messages.join('; ')}`}
          >
            <Icon size={14} />
          </button>
        </TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side="top"
            align="start"
            sideOffset={4}
            className="z-50 max-w-xs rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-md"
          >
            <ul className="space-y-1">
              {messages.map((msg, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className={isError ? 'text-red-500' : 'text-yellow-500'}>•</span>
                  {msg}
                </li>
              ))}
            </ul>
            <TooltipPrimitive.Arrow className="fill-white" />
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  )
}

// ─── Filter bar ───────────────────────────────────────────────────────────────

interface FilterState {
  prodi_id: string
  hari: string
  semester: string
}

const EMPTY_FILTER: FilterState = { prodi_id: '', hari: '', semester: '' }

interface FilterBarProps {
  filters: FilterState
  prodiList: Prodi[]
  onChange: (f: FilterState) => void
  onReset: () => void
}

function FilterBar({ filters, prodiList, onChange, onReset }: FilterBarProps) {
  const hasActive = filters.prodi_id || filters.hari || filters.semester

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <Filter size={14} className="mt-5 shrink-0 text-slate-400" />

      {/* Prodi */}
      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
          Prodi
        </label>
        <select
          value={filters.prodi_id}
          onChange={(e) => onChange({ ...filters, prodi_id: e.target.value })}
          className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Prodi</option>
          {prodiList.map((p) => (
            <option key={p.id} value={p.id}>
              {p.singkat}
            </option>
          ))}
        </select>
      </div>

      {/* Hari */}
      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
          Hari
        </label>
        <select
          value={filters.hari}
          onChange={(e) => onChange({ ...filters, hari: e.target.value })}
          className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Hari</option>
          {HARI_OPTIONS.map((h) => (
            <option key={h} value={h}>
              {h}
            </option>
          ))}
        </select>
      </div>

      {/* Semester */}
      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
          Semester
        </label>
        <select
          value={filters.semester}
          onChange={(e) => onChange({ ...filters, semester: e.target.value })}
          className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Semester</option>
          {SEMESTER_OPTIONS.map((s) => (
            <option key={s} value={String(s)}>
              Semester {s}
            </option>
          ))}
        </select>
      </div>

      {/* Reset */}
      {hasActive && (
        <button
          onClick={onReset}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-200 hover:text-slate-800"
        >
          <X size={12} />
          Reset
        </button>
      )}
    </div>
  )
}

// ─── Columns ──────────────────────────────────────────────────────────────────

function buildColumns(
  canEdit: boolean,
  onEdit: (a: Assignment) => void,
  conflictMap: Map<string, ConflictLog[]>
): ColumnDef<Record<string, unknown>>[] {
  const cols: ColumnDef<Record<string, unknown>>[] = [
  {
    key: '_conflict',
    label: '',
    render: (_val, row) => {
      const a = row as unknown as Assignment
      const conflicts = conflictMap.get(a.id) ?? []
      return <ConflictIndicator conflicts={conflicts} />
    },
  },
  {
    key: 'mk_kelas.mata_kuliah_kode',
    label: 'Kode MK',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return (
        <span className="font-mono text-xs text-slate-600">
          {a.mk_kelas.mata_kuliah_kode}
        </span>
      )
    },
  },
  {
    key: 'mk_kelas.mata_kuliah_nama',
    label: 'Mata Kuliah',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return (
        <div>
          <div className="text-sm font-medium text-slate-800">
            {a.mk_kelas.mata_kuliah_nama}
          </div>
          {a.mk_kelas.kelas && (
            <div className="text-[10px] text-slate-400">Kelas {a.mk_kelas.kelas}</div>
          )}
        </div>
      )
    },
  },
  {
    key: 'mk_kelas.prodi.singkat',
    label: 'Prodi',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return (
        <span className="text-xs text-slate-600">{a.mk_kelas.prodi.singkat}</span>
      )
    },
  },
  {
    key: 'mk_kelas.semester',
    label: 'Smt',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return <span className="text-xs text-slate-600">{a.mk_kelas.semester}</span>
    },
  },
  {
    key: 'mk_kelas.sks',
    label: 'SKS',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return <span className="text-xs text-slate-600">{a.mk_kelas.sks}</span>
    },
  },
  {
    key: 'timeslot.hari',
    label: 'Hari',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return <span className="text-xs text-slate-700">{a.timeslot.hari}</span>
    },
  },
  {
    key: 'timeslot.label',
    label: 'Waktu',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return (
        <span className="whitespace-nowrap text-xs text-slate-600">
          {formatTime(a.timeslot.jam_mulai)}–{formatTime(a.timeslot.jam_selesai)}
        </span>
      )
    },
  },
  {
    key: 'dosen1.nama',
    label: 'Dosen I',
    sortable: true,
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return <span className="text-xs text-slate-700">{a.dosen1.nama}</span>
    },
  },
  {
    key: 'dosen2',
    label: 'Dosen II',
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return a.dosen2 ? (
        <span className="text-xs text-slate-600">{a.dosen2.nama}</span>
      ) : (
        <span className="text-xs text-slate-300">—</span>
      )
    },
  },
  {
    key: 'ruang',
    label: 'Ruang',
    render: (_val, row) => {
      const a = row as unknown as Assignment
      return a.ruang ? (
        <span className="text-xs text-slate-600">{a.ruang.nama}</span>
      ) : (
        <span className="text-xs text-slate-300">—</span>
      )
    },
  },
  ]

  if (canEdit) {
    cols.push({
      key: '_actions',
      label: '',
      render: (_val, row) => {
        const a = row as unknown as Assignment
        return (
          <button
            type="button"
            onClick={() => onEdit(a)}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Edit assignment"
          >
            <Pencil size={13} />
          </button>
        )
      },
    })
  }

  return cols
}

// ─── Pagination state ─────────────────────────────────────────────────────────

interface PaginationBarProps {
  page: number
  total: number
  pageSize: number
  onPage: (p: number) => void
}

function PaginationBar({ page, total, pageSize, onPage }: PaginationBarProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages <= 1) return null

  const pages: number[] = []
  for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
    pages.push(i)
  }

  return (
    <div className="flex items-center justify-between text-xs text-slate-500">
      <span>
        {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} dari {total} data
      </span>
      <div className="flex items-center gap-1">
        <button
          disabled={page === 1}
          onClick={() => onPage(page - 1)}
          className="rounded px-2 py-1 hover:bg-slate-100 disabled:opacity-40"
        >
          ‹
        </button>
        {pages[0] > 1 && <span className="px-1 text-slate-300">…</span>}
        {pages.map((n) => (
          <button
            key={n}
            onClick={() => onPage(n)}
            className={`min-w-[28px] rounded px-1.5 py-0.5 font-medium ${
              n === page
                ? 'bg-slate-900 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {n}
          </button>
        ))}
        {pages[pages.length - 1] < totalPages && (
          <span className="px-1 text-slate-300">…</span>
        )}
        <button
          disabled={page === totalPages}
          onClick={() => onPage(page + 1)}
          className="rounded px-2 py-1 hover:bg-slate-100 disabled:opacity-40"
        >
          ›
        </button>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SesiDetailPage() {
  const { id: sesiId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTER)
  const [page, setPage] = useState(1)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null)
  const [isExporting, setIsExporting] = useState(false)

  const canEdit = !!user && EDITOR_ROLES_PRODI.includes(user.role)
  const canExport = !!user && EXPORT_ROLES.includes(user.role)

  // ── Queries ───────────────────────────────────────────────────────────────

  const { data: sesiList = [] } = useQuery({
    queryKey: ['sesi'],
    queryFn: getSesiList,
  })

  const sesi: SesiJadwal | undefined = sesiList.find((s) => s.id === sesiId)

  const { data: prodiList = [] } = useQuery({
    queryKey: ['prodi'],
    queryFn: getProdi,
  })

  const queryParams: AssignmentListParams = {
    page,
    page_size: PAGE_SIZE,
    ...(filters.prodi_id && { prodi_id: filters.prodi_id }),
    ...(filters.hari && { hari: filters.hari }),
    ...(filters.semester && { semester: Number(filters.semester) }),
  }

  const {
    data: assignmentData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['assignments', sesiId, queryParams],
    queryFn: () => getAssignments(sesiId!, queryParams),
    enabled: !!sesiId,
  })

  const { data: conflictList = [] } = useQuery({
    queryKey: ['conflicts', sesiId],
    queryFn: () => getConflicts(sesiId!),
    enabled: !!sesiId,
  })

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleFilterChange = useCallback((f: FilterState) => {
    setFilters(f)
    setPage(1)
  }, [])

  const handleFilterReset = useCallback(() => {
    setFilters(EMPTY_FILTER)
    setPage(1)
  }, [])

  const handleExport = useCallback(async () => {
    if (!sesiId) return
    setIsExporting(true)
    try {
      await exportJadwal(sesiId, sesi?.nama)
    } finally {
      setIsExporting(false)
    }
  }, [sesiId, sesi?.nama])

  // ── Derived ───────────────────────────────────────────────────────────────

  const assignments = (assignmentData?.items ?? []) as unknown as Record<string, unknown>[]
  const total = assignmentData?.total ?? 0

  const conflictMap = useMemo(() => buildConflictMap(conflictList), [conflictList])

  const columns = buildColumns(canEdit, setEditingAssignment, conflictMap)

  const rowClassName = useCallback(
    (row: Record<string, unknown>) => {
      const a = row as unknown as Assignment
      const conflicts = conflictMap.get(a.id) ?? []
      const sev = topSeverity(conflicts)
      if (sev === 'ERROR') return 'bg-red-50 border-l-4 border-red-500'
      if (sev === 'WARNING') return 'bg-yellow-50 border-l-4 border-yellow-400'
      return ''
    },
    [conflictMap]
  )

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/sesi')}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Kembali"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-base font-semibold text-slate-900">
              {sesi ? sesi.nama : 'Detail Sesi'}
            </h1>
            {sesi && (
              <div className="mt-0.5 flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  {sesi.semester} {sesi.tahun_akademik}
                </span>
                <Badge variant={sesi.status} size="sm">
                  {sesi.status}
                </Badge>
              </div>
            )}
          </div>
        </div>

        {/* Stats + Actions */}
        <div className="flex items-center gap-3">
          {!isLoading && (
            <div className="text-right">
              <div className="text-lg font-semibold text-slate-800">{total}</div>
              <div className="text-[10px] text-slate-400">total assignment</div>
            </div>
          )}
          <Link
            to={`/sesi/${sesiId}/konflik`}
            className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <ShieldAlert size={14} />
            Konflik
          </Link>
          <Link
            to={`/sesi/${sesiId}/team-teaching`}
            className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Users size={14} />
            Team Teaching
          </Link>
          {canExport && (
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download size={14} />
              {isExporting ? 'Mengunduh...' : 'Export'}
            </button>
          )}
          {canEdit && (
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
            >
              <Plus size={14} />
              Tambah Assignment
            </button>
          )}
        </div>
      </div>

      {/* Filter bar */}
      <FilterBar
        filters={filters}
        prodiList={prodiList}
        onChange={handleFilterChange}
        onReset={handleFilterReset}
      />

      {/* Error */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data assignment. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={assignments}
        loading={isLoading}
        emptyMessage="Tidak ada assignment yang sesuai filter."
        pageSize={PAGE_SIZE}
        rowClassName={rowClassName}
      />

      {/* Server-side pagination */}
      {!isLoading && total > PAGE_SIZE && (
        <PaginationBar
          page={page}
          total={total}
          pageSize={PAGE_SIZE}
          onPage={setPage}
        />
      )}

      {/* Add Assignment Modal */}
      {sesiId && (
        <AddAssignmentModal
          open={showAddModal}
          onClose={() => setShowAddModal(false)}
          sesiId={sesiId}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['assignments', sesiId] })
          }}
        />
      )}

      {/* Edit Assignment Modal */}
      {sesiId && editingAssignment && (
        <EditAssignmentModal
          open={!!editingAssignment}
          onClose={() => setEditingAssignment(null)}
          sesiId={sesiId}
          assignment={editingAssignment}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['assignments', sesiId] })
          }}
        />
      )}
    </div>
  )
}
