import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge } from '@/components/Badge'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { getSesiList } from '@/api/sesi'
import { getPreferencesSummary, type DosenPreferenceSummaryItem } from '@/api/report'

// ─── Types ────────────────────────────────────────────────────────────────────

type FaseFilter = 'all' | 'pre_schedule' | 'post_draft'

type RowData = DosenPreferenceSummaryItem & {
  dipenuhi: number
  pct_dipenuhi: number
} & Record<string, unknown>

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pctBadgeVariant(pct: number): string {
  if (pct >= 80) return 'success'
  if (pct >= 50) return 'WARNING'
  return 'ERROR'
}

function rowBgClass(row: RowData): string {
  if (row.total_dilanggar > 0 && row.pct_dipenuhi < 50) return 'bg-red-50'
  if (row.total_dilanggar > 0) return 'bg-amber-50'
  return ''
}

// ─── Columns ──────────────────────────────────────────────────────────────────

const COLUMNS: ColumnDef<RowData>[] = [
  {
    key: 'kode',
    label: 'Kode',
    sortable: true,
    render: (val) => (
      <span className="font-mono text-xs text-slate-500">{String(val ?? '')}</span>
    ),
  },
  {
    key: 'nama',
    label: 'Nama Dosen',
    sortable: true,
  },
  {
    key: 'total_preferensi',
    label: 'Diajukan',
    sortable: true,
    render: (val) => (
      <span className="tabular-nums font-medium">{String(val ?? 0)}</span>
    ),
  },
  {
    key: 'dipenuhi',
    label: 'Dipenuhi',
    sortable: true,
    render: (val) => (
      <span className="tabular-nums text-green-700 font-medium">{String(val ?? 0)}</span>
    ),
  },
  {
    key: 'total_dilanggar',
    label: 'Dilanggar',
    sortable: true,
    render: (val) => {
      const n = val as number
      return (
        <span className={`tabular-nums font-medium ${n > 0 ? 'text-red-600' : 'text-slate-400'}`}>
          {n > 0 ? n : '—'}
        </span>
      )
    },
  },
  {
    key: 'pct_dipenuhi',
    label: '% Dipenuhi',
    sortable: true,
    render: (val, row) => {
      const pct = val as number
      if (row.total_preferensi === 0) {
        return <span className="text-slate-300 text-xs">—</span>
      }
      return (
        <Badge variant={pctBadgeVariant(pct)} size="sm">
          {pct.toFixed(0)}%
        </Badge>
      )
    },
  },
]

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PreferensiSummaryPage() {
  const [sesiId, setSesiId] = useState<string>('')
  const [fase, setFase] = useState<FaseFilter>('all')

  const { data: sesiList = [], isLoading: sesiLoading } = useQuery({
    queryKey: ['sesi-list'],
    queryFn: getSesiList,
  })

  const { data: summary, isLoading: summaryLoading, error } = useQuery({
    queryKey: ['preferences-summary', sesiId],
    queryFn: () => getPreferencesSummary(sesiId),
    enabled: !!sesiId,
  })

  // Build rows with derived fields
  const rows: RowData[] = useMemo(() => {
    if (!summary) return []
    return summary.breakdown.map((item) => {
      const dipenuhi = item.total_preferensi - item.total_dilanggar
      const pct_dipenuhi =
        item.total_preferensi > 0 ? (dipenuhi / item.total_preferensi) * 100 : 0
      return { ...item, dipenuhi, pct_dipenuhi } as RowData
    })
  }, [summary])

  // Summary stats
  const totalDipenuhi = summary
    ? summary.total_preferensi - summary.total_dilanggar
    : 0

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Ringkasan Preferensi Dosen</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Rekap pemenuhan preferensi hari mengajar per dosen dalam satu sesi jadwal.
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm font-medium text-slate-700 whitespace-nowrap">
          Sesi Jadwal:
        </label>
        <select
          className="border border-slate-200 rounded-md px-3 py-1.5 text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[240px]"
          value={sesiId}
          onChange={(e) => setSesiId(e.target.value)}
          disabled={sesiLoading}
        >
          <option value="">— Pilih sesi —</option>
          {sesiList.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nama} ({s.semester} {s.tahun_akademik})
            </option>
          ))}
        </select>

        <label className="text-sm font-medium text-slate-700 whitespace-nowrap ml-2">
          Fase:
        </label>
        <select
          className="border border-slate-200 rounded-md px-3 py-1.5 text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={fase}
          onChange={(e) => setFase(e.target.value as FaseFilter)}
        >
          <option value="all">Semua Fase</option>
          <option value="pre_schedule">Pre-Schedule</option>
          <option value="post_draft">Post-Draft</option>
        </select>

        {fase !== 'all' && (
          <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1">
            Filter fase belum didukung oleh server — menampilkan semua fase
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Gagal memuat data ringkasan preferensi. Coba lagi.
        </div>
      )}

      {/* Empty / prompt state */}
      {!sesiId && !summaryLoading && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-slate-400">
          Pilih sesi jadwal untuk melihat ringkasan preferensi.
        </div>
      )}

      {/* Stats cards */}
      {sesiId && summary && (
        <div className="grid grid-cols-3 gap-4 max-w-lg">
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs text-slate-500">Total Diajukan</p>
            <p className="text-2xl font-semibold text-slate-800 tabular-nums mt-0.5">
              {summary.total_preferensi}
            </p>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3">
            <p className="text-xs text-green-600">Dipenuhi</p>
            <p className="text-2xl font-semibold text-green-700 tabular-nums mt-0.5">
              {totalDipenuhi}
            </p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-xs text-red-600">Dilanggar</p>
            <p className="text-2xl font-semibold text-red-700 tabular-nums mt-0.5">
              {summary.total_dilanggar}
            </p>
          </div>
        </div>
      )}

      {/* Table */}
      {sesiId && (
        <DataTable<RowData>
          columns={COLUMNS}
          data={rows}
          loading={summaryLoading}
          pageSize={50}
          emptyMessage="Tidak ada data preferensi untuk sesi ini."
          rowClassName={rowBgClass}
        />
      )}

      {/* Legend */}
      {sesiId && summary && rows.length > 0 && (
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="font-medium">Keterangan:</span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-red-100 border border-red-300" />
            Pemenuhan &lt; 50%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-amber-100 border border-amber-300" />
            Ada preferensi dilanggar
          </span>
        </div>
      )}
    </div>
  )
}
