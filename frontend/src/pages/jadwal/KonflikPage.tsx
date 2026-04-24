import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, AlertCircle, AlertTriangle, RefreshCw, CheckCircle } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { Badge } from '@/components/Badge'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { useAuthStore } from '@/store/authStore'
import {
  getConflicts,
  checkConflicts,
  resolveConflict,
  ConflictLog,
} from '@/api/conflict'
import { getSesiList } from '@/api/sesi'

// ─── RBAC ─────────────────────────────────────────────────────────────────────

const EDITOR_ROLES_PRODI = [
  'admin',
  'sekretaris_jurusan',
  'tendik_jurusan',
  'koordinator_prodi',
  'tendik_prodi',
]

const EDITOR_ROLES_JURUSAN = ['admin', 'sekretaris_jurusan', 'tendik_jurusan']

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ─── Summary Cards ────────────────────────────────────────────────────────────

interface SummaryCardsProps {
  errorCount: number
  warningCount: number
  lastChecked: string | null
}

function SummaryCards({ errorCount, warningCount, lastChecked }: SummaryCardsProps) {
  return (
    <div className="flex flex-wrap items-stretch gap-3">
      {/* ERROR card */}
      <div className="flex min-w-[140px] items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
        <AlertCircle size={20} className="shrink-0 text-red-500" />
        <div>
          <div className="text-2xl font-bold text-red-700">{errorCount}</div>
          <div className="text-xs font-medium text-red-500">ERROR</div>
        </div>
      </div>

      {/* WARNING card */}
      <div className="flex min-w-[140px] items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
        <AlertTriangle size={20} className="shrink-0 text-amber-500" />
        <div>
          <div className="text-2xl font-bold text-amber-700">{warningCount}</div>
          <div className="text-xs font-medium text-amber-500">WARNING</div>
        </div>
      </div>

      {/* Last checked */}
      {lastChecked && (
        <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
              Terakhir diperiksa
            </div>
            <div className="text-xs text-slate-600">{formatDateTime(lastChecked)}</div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function KonflikPage() {
  const { id: sesiId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'ERROR' | 'WARNING'>('ALL')
  const [jenisFilter, setJenisFilter] = useState<string>('ALL')
  const [pendingResolveId, setPendingResolveId] = useState<string | null>(null)

  const canCheck = !!user && EDITOR_ROLES_PRODI.includes(user.role)
  const canResolve = !!user && EDITOR_ROLES_JURUSAN.includes(user.role)

  // ── Queries ───────────────────────────────────────────────────────────────

  const { data: sesiList = [] } = useQuery({
    queryKey: ['sesi'],
    queryFn: getSesiList,
  })

  const sesi = sesiList.find((s) => s.id === sesiId)

  const {
    data: conflicts = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['conflicts', sesiId],
    queryFn: () => getConflicts(sesiId!),
    enabled: !!sesiId,
  })

  // ── Mutations ─────────────────────────────────────────────────────────────

  const checkMutation = useMutation({
    mutationFn: () => checkConflicts(sesiId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conflicts', sesiId] })
    },
  })

  const resolveMutation = useMutation({
    mutationFn: (conflictId: string) => resolveConflict(sesiId!, conflictId),
    onSuccess: () => {
      setPendingResolveId(null)
      queryClient.invalidateQueries({ queryKey: ['conflicts', sesiId] })
    },
  })

  // ── Derived ───────────────────────────────────────────────────────────────

  const errorCount = conflicts.filter((c) => c.severity === 'ERROR').length
  const warningCount = conflicts.filter((c) => c.severity === 'WARNING').length
  const lastChecked = conflicts.length > 0 ? conflicts[0].checked_at : null

  const availableJenis = Array.from(new Set(conflicts.map((c) => c.jenis))).sort()

  const filteredConflicts = conflicts.filter((c) => {
    const matchesSeverity = severityFilter === 'ALL' || c.severity === severityFilter
    const matchesJenis = jenisFilter === 'ALL' || c.jenis === jenisFilter
    return matchesSeverity && matchesJenis
  })

  // ── Columns ───────────────────────────────────────────────────────────────

  const columns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: 'jenis',
      label: 'Jenis',
      sortable: true,
      render: (_val, row) => {
        const c = row as unknown as ConflictLog
        return (
          <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700">
            {c.jenis}
          </span>
        )
      },
    },
    {
      key: 'severity',
      label: 'Severity',
      sortable: true,
      render: (_val, row) => {
        const c = row as unknown as ConflictLog
        return (
          <Badge variant={c.severity} size="sm">
            {c.severity}
          </Badge>
        )
      },
    },
    {
      key: 'pesan',
      label: 'Pesan',
      render: (_val, row) => {
        const c = row as unknown as ConflictLog
        return <span className="text-sm text-slate-700">{c.pesan}</span>
      },
    },
    {
      key: 'assignment_ids',
      label: 'Terlibat',
      render: (_val, row) => {
        const c = row as unknown as ConflictLog
        const n = c.assignment_ids.length
        return (
          <span className="text-xs text-slate-500">
            {n} assignment
          </span>
        )
      },
    },
    {
      key: 'is_resolved',
      label: 'Status',
      sortable: true,
      render: (_val, row) => {
        const c = row as unknown as ConflictLog
        if (c.is_resolved) {
          return (
            <Badge variant="success" size="sm">
              Resolved
            </Badge>
          )
        }
        return (
          <div className="flex items-center gap-2">
            <Badge variant="default" size="sm">
              Aktif
            </Badge>
            {canResolve && (
              <button
                type="button"
                disabled={resolveMutation.isPending}
                onClick={() => setPendingResolveId(c.id)}
                className="flex items-center gap-1 rounded border border-green-200 bg-green-50 px-2 py-0.5 text-[11px] font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
              >
                <CheckCircle size={11} />
                Tandai Resolved
              </button>
            )}
          </div>
        )
      },
    },
  ]

  // ── Render ────────────────────────────────────────────────────────────────

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
            <h1 className="text-base font-semibold text-slate-900">
              Konflik Jadwal
            </h1>
            {sesi && (
              <div className="mt-0.5 text-xs text-slate-500">
                {sesi.nama} — {sesi.semester} {sesi.tahun_akademik}
              </div>
            )}
          </div>
        </div>

        {/* Periksa Konflik button */}
        {canCheck && (
          <button
            type="button"
            disabled={checkMutation.isPending}
            onClick={() => checkMutation.mutate()}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
          >
            <RefreshCw size={14} className={checkMutation.isPending ? 'animate-spin' : ''} />
            {checkMutation.isPending ? 'Memeriksa...' : 'Periksa Konflik'}
          </button>
        )}
      </div>

      {/* Check error */}
      {checkMutation.isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal menjalankan pemeriksaan konflik. Silakan coba lagi.
        </div>
      )}

      {/* Summary cards */}
      {!isLoading && (
        <SummaryCards
          errorCount={errorCount}
          warningCount={warningCount}
          lastChecked={lastChecked}
        />
      )}

      {/* Severity filter */}
      <div className="flex flex-wrap items-center gap-2">
        {(['ALL', 'ERROR', 'WARNING'] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setSeverityFilter(v)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              severityFilter === v
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
            }`}
          >
            {v === 'ALL' ? 'Semua' : v}
          </button>
        ))}

        {availableJenis.length > 0 && (
          <>
            <span className="mx-1 h-4 w-px bg-slate-200" />
            <button
              type="button"
              onClick={() => setJenisFilter('ALL')}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                jenisFilter === 'ALL'
                  ? 'bg-slate-900 text-white'
                  : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              Semua Jenis
            </button>
            {availableJenis.map((jenis) => (
              <button
                key={jenis}
                type="button"
                onClick={() => setJenisFilter(jenis)}
                className={`rounded-full px-3 py-1 font-mono text-xs font-medium transition-colors ${
                  jenisFilter === jenis
                    ? 'bg-slate-900 text-white'
                    : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                {jenis}
              </button>
            ))}
          </>
        )}
      </div>

      {/* Fetch error */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data konflik. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={filteredConflicts as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Tidak ada konflik ditemukan."
        pageSize={20}
        rowClassName={(row) => {
          const c = row as unknown as ConflictLog
          return c.is_resolved ? 'opacity-50' : ''
        }}
      />

      {/* Confirm resolve dialog */}
      <ConfirmDialog
        open={pendingResolveId !== null}
        onClose={() => setPendingResolveId(null)}
        onConfirm={() => {
          if (pendingResolveId) resolveMutation.mutate(pendingResolveId)
        }}
        title="Tandai Konflik sebagai Resolved"
        message="Konflik ini akan ditandai sebagai resolved. Tindakan ini tidak dapat dibatalkan secara otomatis."
        confirmLabel="Tandai Resolved"
        cancelLabel="Batal"
        variant="warning"
        loading={resolveMutation.isPending}
      />
    </div>
  )
}
