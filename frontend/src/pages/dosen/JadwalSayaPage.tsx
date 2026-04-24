import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarDays } from 'lucide-react'

import { getSesiList, SesiJadwal } from '@/api/sesi'
import { getDosenJadwal, DosenJadwalItem } from '@/api/dosen'

// ─── Constants ────────────────────────────────────────────────────────────────

const HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat'] as const

const SESI_INFO = [
  { sesi: 1, label: 'Sesi 1', jam: '07:30–10:00' },
  { sesi: 2, label: 'Sesi 2', jam: '10:00–12:30' },
  { sesi: 3, label: 'Sesi 3', jam: '13:00–15:30' },
] as const

// ─── Build weekly grid ────────────────────────────────────────────────────────

type GridCell = DosenJadwalItem | null
type WeeklyGrid = Record<number, Record<string, GridCell>>

function buildGrid(items: DosenJadwalItem[]): WeeklyGrid {
  const grid: WeeklyGrid = {}
  for (const s of SESI_INFO) {
    grid[s.sesi] = {}
    for (const h of HARI) {
      grid[s.sesi][h] = null
    }
  }
  for (const item of items) {
    const { hari, sesi } = item.timeslot
    if (grid[sesi] && hari in grid[sesi]) {
      grid[sesi][hari] = item
    }
  }
  return grid
}

// ─── Cell component ───────────────────────────────────────────────────────────

function ScheduleCell({ item }: { item: DosenJadwalItem | null }) {
  if (!item) {
    return <td className="border border-slate-200 bg-white p-2 align-top h-20" />
  }

  return (
    <td className="border border-slate-200 bg-blue-50 p-2 align-top h-20">
      <div className="space-y-0.5">
        <div className="text-xs font-semibold text-blue-900 leading-tight">
          {item.mk_kelas.mata_kuliah_nama}
        </div>
        {item.mk_kelas.kelas && (
          <div className="text-[10px] text-blue-700">
            Kelas {item.mk_kelas.kelas}
          </div>
        )}
        {item.ruang && (
          <div className="text-[10px] text-slate-500">
            {item.ruang.nama}
          </div>
        )}
        <div className="text-[10px] text-slate-400">
          {item.mk_kelas.sks} SKS · Smt {item.mk_kelas.semester}
        </div>
      </div>
    </td>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function JadwalSayaPage() {
  const [selectedSesiId, setSelectedSesiId] = useState<string>('')

  // Fetch sesi list
  const { data: sesiList = [], isLoading: sesiLoading } = useQuery({
    queryKey: ['sesi'],
    queryFn: getSesiList,
    select: (data: SesiJadwal[]) =>
      data.filter((s) => s.status === 'Aktif' || s.status === 'Draft'),
  })

  // Auto-select first sesi when list loads
  const effectiveSesiId = selectedSesiId || sesiList[0]?.id || ''

  // Fetch assignments for selected sesi (backend filters by dosen role automatically)
  const {
    data: jadwalData,
    isLoading: jadwalLoading,
    isError,
  } = useQuery({
    queryKey: ['dosen-jadwal', effectiveSesiId],
    queryFn: () => getDosenJadwal(effectiveSesiId),
    enabled: !!effectiveSesiId,
  })

  const items = jadwalData?.items ?? []
  const grid = buildGrid(items)
  const selectedSesi = sesiList.find((s) => s.id === effectiveSesiId)

  const isLoading = sesiLoading || jadwalLoading

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <CalendarDays size={18} className="text-slate-500" />
          <div>
            <h1 className="text-base font-semibold text-slate-900">Jadwal Saya</h1>
            <p className="text-xs text-slate-500 mt-0.5">Jadwal mengajar minggu ini</p>
          </div>
        </div>

        {/* Sesi selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Sesi Jadwal:</label>
          <select
            value={effectiveSesiId}
            onChange={(e) => setSelectedSesiId(e.target.value)}
            disabled={sesiLoading}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:opacity-50"
          >
            {sesiList.length === 0 && (
              <option value="">— Tidak ada sesi aktif —</option>
            )}
            {sesiList.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nama} ({s.semester} {s.tahun_akademik})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Sesi info badge */}
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
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat jadwal. Silakan coba lagi.
        </div>
      )}

      {/* No sesi */}
      {!sesiLoading && sesiList.length === 0 && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-6 py-10 text-center">
          <CalendarDays size={32} className="mx-auto mb-2 text-slate-300" />
          <p className="text-sm text-slate-500">Tidak ada sesi jadwal aktif saat ini.</p>
        </div>
      )}

      {/* Weekly grid */}
      {effectiveSesiId && !isError && (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-sm text-slate-400">
              Memuat jadwal…
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <CalendarDays size={32} className="mb-2 text-slate-300" />
              <p className="text-sm text-slate-500">Belum ada jadwal mengajar untuk sesi ini.</p>
            </div>
          ) : (
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50">
                  <th className="border border-slate-200 px-3 py-2 text-left text-xs font-medium text-slate-500 w-28">
                    Sesi / Hari
                  </th>
                  {HARI.map((h) => (
                    <th
                      key={h}
                      className="border border-slate-200 px-3 py-2 text-center text-xs font-medium text-slate-700"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SESI_INFO.map(({ sesi, label, jam }) => (
                  <tr key={sesi}>
                    <td className="border border-slate-200 bg-slate-50 px-3 py-2 align-middle">
                      <div className="text-xs font-medium text-slate-700">{label}</div>
                      <div className="text-[10px] text-slate-400">{jam}</div>
                    </td>
                    {HARI.map((h) => (
                      <ScheduleCell key={h} item={grid[sesi][h]} />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Legend */}
      {items.length > 0 && (
        <div className="flex items-center gap-4 text-[10px] text-slate-400">
          <span className="flex items-center gap-1">
            <span className="inline-block h-3 w-3 rounded bg-blue-50 border border-blue-200" />
            Mata kuliah yang diampu
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-3 w-3 rounded bg-white border border-slate-200" />
            Slot kosong
          </span>
        </div>
      )}
    </div>
  )
}
