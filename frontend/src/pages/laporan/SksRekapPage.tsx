import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/Badge'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { getSesiList } from '@/api/sesi'
import { getSksRekap, type DosenSksRekap } from '@/api/report'

// ─── Constants ────────────────────────────────────────────────────────────────

const PRODI_COLS = ['S1 MTK', 'S1 STK', 'S2 MTK', 'Layanan']
const BKD_MAX = 12 // default visual max for progress bar

// ─── BKD flag helpers ─────────────────────────────────────────────────────────

function bkdBadgeVariant(flag: DosenSksRekap['bkd_flag']) {
  if (flag === 'over_limit') return 'ERROR'
  if (flag === 'near_limit') return 'WARNING'
  if (flag === 'ok') return 'success'
  return 'default'
}

function bkdBadgeLabel(flag: DosenSksRekap['bkd_flag']) {
  if (flag === 'over_limit') return 'Melebihi BKD'
  if (flag === 'near_limit') return 'Mendekati BKD'
  if (flag === 'ok') return 'OK'
  return '—'
}

function rowBgClass(flag: DosenSksRekap['bkd_flag']) {
  if (flag === 'over_limit') return 'bg-red-50'
  if (flag === 'near_limit') return 'bg-amber-50'
  return ''
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function SksBar({ total, limit, flag }: { total: number; limit: number | null; flag: DosenSksRekap['bkd_flag'] }) {
  const max = limit ?? BKD_MAX
  const pct = Math.min((total / max) * 100, 100)

  const barColor =
    flag === 'over_limit'
      ? 'bg-red-500'
      : flag === 'near_limit'
      ? 'bg-amber-400'
      : 'bg-blue-500'

  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 rounded-full bg-slate-200 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-600 tabular-nums w-10 text-right">
        {total} / {max}
      </span>
    </div>
  )
}

// ─── Row type for DataTable ───────────────────────────────────────────────────

type RowData = DosenSksRekap & Record<string, unknown>

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SksRekapPage() {
  const [sesiId, setSesiId] = useState<string>('')

  const { data: sesiList = [], isLoading: sesiLoading } = useQuery({
    queryKey: ['sesi-list'],
    queryFn: getSesiList,
  })

  const { data: rekap, isLoading: rekapLoading, error } = useQuery({
    queryKey: ['sks-rekap', sesiId],
    queryFn: () => getSksRekap(sesiId),
    enabled: !!sesiId,
  })

  // Build columns dynamically based on prodi breakdown keys present in data
  const prodiKeys = rekap
    ? Array.from(new Set(rekap.items.flatMap((r) => Object.keys(r.breakdown))))
    : PRODI_COLS

  const columns: ColumnDef<RowData>[] = [
    {
      key: 'dosen_kode',
      label: 'Kode',
      sortable: true,
      render: (val) => <span className="font-mono text-xs text-slate-500">{String(val ?? '')}</span>,
    },
    {
      key: 'dosen_nama',
      label: 'Nama Dosen',
      sortable: true,
    },
    ...prodiKeys.map((prodi) => ({
      key: `breakdown.${prodi}`,
      label: prodi,
      sortable: true,
      render: (_val: unknown, row: RowData) => {
        const val = (row.breakdown as Record<string, number>)[prodi] ?? 0
        return <span className="tabular-nums">{val > 0 ? val : <span className="text-slate-300">—</span>}</span>
      },
    })),
    {
      key: 'total_sks',
      label: 'Total SKS',
      sortable: true,
      render: (val) => <span className="font-semibold tabular-nums">{String(val ?? 0)}</span>,
    },
    {
      key: 'total_sks',
      label: 'Beban',
      render: (_val, row) => (
        <SksBar total={row.total_sks as number} limit={row.bkd_limit_sks as number | null} flag={row.bkd_flag as DosenSksRekap['bkd_flag']} />
      ),
    },
    {
      key: 'bkd_flag',
      label: 'Status BKD',
      render: (val) => {
        const flag = val as DosenSksRekap['bkd_flag']
        if (flag === 'no_limit') return <span className="text-slate-400 text-xs">Tidak ada limit</span>
        return <Badge variant={bkdBadgeVariant(flag)} size="sm">{bkdBadgeLabel(flag)}</Badge>
      },
    },
  ]

  const rows: RowData[] = (rekap?.items ?? []) as RowData[]

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Rekap Beban SKS Dosen</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Ringkasan beban mengajar per dosen, dikelompokkan per program studi.
        </p>
      </div>

      {/* Sesi selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-slate-700 whitespace-nowrap">Sesi Jadwal:</label>
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
        {rekap && (
          <span className="text-xs text-slate-400">{rekap.total_dosen} dosen</span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Gagal memuat data rekap SKS. Coba lagi.
        </div>
      )}

      {/* Empty / prompt state */}
      {!sesiId && !rekapLoading && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-slate-400">
          Pilih sesi jadwal untuk melihat rekap SKS.
        </div>
      )}

      {/* Table */}
      {sesiId && (
        <DataTable<RowData>
          columns={columns}
          data={rows}
          loading={rekapLoading}
          pageSize={50}
          emptyMessage="Tidak ada data dosen untuk sesi ini."
          rowClassName={(row) => rowBgClass(row.bkd_flag as DosenSksRekap['bkd_flag'])}
        />
      )}

      {/* Legend */}
      {sesiId && rekap && (
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="font-medium">Keterangan:</span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-red-100 border border-red-300" />
            Melebihi BKD
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-amber-100 border border-amber-300" />
            Mendekati BKD
          </span>
          <span className="text-slate-400">Bar menunjukkan total SKS relatif terhadap limit BKD (default {BKD_MAX} SKS).</span>
        </div>
      )}
    </div>
  )
}
