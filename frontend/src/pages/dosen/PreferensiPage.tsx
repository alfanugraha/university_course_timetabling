import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BanIcon, CheckCircle2, Save, AlertCircle } from 'lucide-react'

import { useAuthStore } from '@/store/authStore'
import { getTimeslots, Timeslot } from '@/api/timeslot'
import {
  getDosen,
  getDosenUnavailability,
  addDosenUnavailability,
  deleteDosenUnavailability,
  DosenUnavailabilityItem,
} from '@/api/dosen'

// ─── Constants ────────────────────────────────────────────────────────────────

const HARI_LIST = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat'] as const
type Hari = (typeof HARI_LIST)[number]

const SESI_INFO = [
  { sesi: 1, label: 'Sesi 1', jam: '07:30–10:00' },
  { sesi: 2, label: 'Sesi 2', jam: '10:00–12:30' },
  { sesi: 3, label: 'Sesi 3', jam: '13:00–15:30' },
] as const

// Map hari string from backend to display label
const HARI_MAP: Record<string, Hari> = {
  Senin: 'Senin',
  Selasa: 'Selasa',
  Rabu: 'Rabu',
  Kamis: 'Kamis',
  Jumat: 'Jumat',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Build a lookup: hari → sesi → Timeslot */
function buildTimeslotGrid(timeslots: Timeslot[]): Record<Hari, Record<number, Timeslot>> {
  const grid = {} as Record<Hari, Record<number, Timeslot>>
  for (const h of HARI_LIST) {
    grid[h] = {}
  }
  for (const ts of timeslots) {
    const hari = HARI_MAP[ts.hari]
    if (hari) {
      grid[hari][ts.sesi] = ts
    }
  }
  return grid
}

/** Build a Set of timeslot_ids that are currently unavailable */
function buildUnavailSet(items: DosenUnavailabilityItem[]): Set<string> {
  return new Set(items.map((i) => i.timeslot_id))
}

/** Build a map: timeslot_id → unavailability record id */
function buildUnavailIdMap(items: DosenUnavailabilityItem[]): Map<string, string> {
  return new Map(items.map((i) => [i.timeslot_id, i.id]))
}

// ─── Cell Component ───────────────────────────────────────────────────────────

interface CellProps {
  timeslot: Timeslot | undefined
  isUnavailable: boolean
  onToggle: () => void
}

function TimeslotCell({ timeslot, isUnavailable, onToggle }: CellProps) {
  if (!timeslot) {
    return <td className="border border-slate-200 bg-slate-50 p-2 h-20" />
  }

  return (
    <td className="border border-slate-200 p-1.5 h-20 align-top">
      <button
        type="button"
        onClick={onToggle}
        className={[
          'w-full h-full rounded-md flex flex-col items-center justify-center gap-1 transition-all text-xs font-medium border',
          isUnavailable
            ? 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100'
            : 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100',
        ].join(' ')}
        title={isUnavailable ? 'Klik untuk tandai tersedia' : 'Klik untuk tandai tidak tersedia'}
      >
        {isUnavailable ? (
          <>
            <BanIcon size={14} className="text-red-500" />
            <span className="text-[10px] text-red-600">Tidak Tersedia</span>
          </>
        ) : (
          <>
            <CheckCircle2 size={14} className="text-green-500" />
            <span className="text-[10px] text-green-600">Tersedia</span>
          </>
        )}
      </button>
    </td>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PreferensiPage() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  // Local toggle state: Set of timeslot_ids marked unavailable
  const [localUnavail, setLocalUnavail] = useState<Set<string>>(new Set())
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  // We need the dosen record linked to this user (dosen.user_id === user.id)
  // to get the dosen.id for the unavailability API calls

  const { data: timeslots = [], isLoading: tsLoading } = useQuery({
    queryKey: ['timeslots'],
    queryFn: getTimeslots,
  })

  // Fetch dosen list to find current user's dosen record
  const { data: dosenList = [], isLoading: dosenLoading } = useQuery({
    queryKey: ['dosen-all'],
    queryFn: () => getDosen(),
    enabled: !!user,
  })

  const myDosen = dosenList.find((d) => d.user_id === user?.id)
  const dosenId = myDosen?.id ?? null

  const {
    data: unavailData = [],
    isLoading: unavailLoading,
    isError: unavailError,
  } = useQuery({
    queryKey: ['dosen-unavailability', dosenId],
    queryFn: () => getDosenUnavailability(dosenId!),
    enabled: !!dosenId,
  })

  // Sync server state → local state on load
  useEffect(() => {
    if (unavailData.length >= 0) {
      setLocalUnavail(buildUnavailSet(unavailData))
    }
  }, [unavailData])

  const isLoading = tsLoading || dosenLoading || unavailLoading
  const tsGrid = buildTimeslotGrid(timeslots)

  function handleToggle(timeslotId: string) {
    setLocalUnavail((prev) => {
      const next = new Set(prev)
      if (next.has(timeslotId)) {
        next.delete(timeslotId)
      } else {
        next.add(timeslotId)
      }
      return next
    })
    // Reset save status on any change
    setSaveStatus('idle')
  }

  async function handleSave() {
    if (!dosenId) return

    setSaveStatus('saving')
    setSaveError(null)

    const savedSet = buildUnavailSet(unavailData)
    const savedIdMap = buildUnavailIdMap(unavailData)

    // Slots to add: in localUnavail but not in savedSet
    const toAdd = [...localUnavail].filter((id) => !savedSet.has(id))
    // Slots to remove: in savedSet but not in localUnavail
    const toRemove = [...savedSet].filter((id) => !localUnavail.has(id))

    try {
      await Promise.all([
        ...toAdd.map((tsId) => addDosenUnavailability(dosenId, tsId)),
        ...toRemove.map((tsId) => {
          const unavailId = savedIdMap.get(tsId)
          if (unavailId) return deleteDosenUnavailability(dosenId, unavailId)
          return Promise.resolve()
        }),
      ])

      await queryClient.invalidateQueries({ queryKey: ['dosen-unavailability', dosenId] })
      setSaveStatus('success')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal menyimpan perubahan'
      setSaveError(msg)
      setSaveStatus('error')
    }
  }

  // Detect unsaved changes
  const savedSet = buildUnavailSet(unavailData)
  const hasChanges =
    [...localUnavail].some((id) => !savedSet.has(id)) ||
    [...savedSet].some((id) => !localUnavail.has(id))

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <BanIcon size={18} className="text-slate-500" />
          <div>
            <h1 className="text-base font-semibold text-slate-900">Preferensi Unavailability</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Tandai slot waktu yang Anda tidak tersedia untuk mengajar
            </p>
          </div>
        </div>

        {/* Save button */}
        <button
          type="button"
          onClick={handleSave}
          disabled={!dosenId || saveStatus === 'saving' || !hasChanges}
          className={[
            'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
            hasChanges && dosenId
              ? 'bg-slate-800 text-white hover:bg-slate-700'
              : 'bg-slate-100 text-slate-400 cursor-not-allowed',
          ].join(' ')}
        >
          <Save size={14} />
          {saveStatus === 'saving' ? 'Menyimpan…' : 'Simpan'}
        </button>
      </div>

      {/* Success / Error feedback */}
      {saveStatus === 'success' && (
        <div className="flex items-center gap-2 rounded-md bg-green-50 px-4 py-2.5 text-sm text-green-700">
          <CheckCircle2 size={15} />
          Perubahan berhasil disimpan.
        </div>
      )}
      {saveStatus === 'error' && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 px-4 py-2.5 text-sm text-red-700">
          <AlertCircle size={15} />
          {saveError ?? 'Gagal menyimpan perubahan.'}
        </div>
      )}

      {/* No dosen record linked */}
      {!dosenLoading && !myDosen && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Akun Anda belum terhubung ke data dosen. Hubungi administrator.
        </div>
      )}

      {/* Error loading unavailability */}
      {unavailError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data unavailability. Silakan coba lagi.
        </div>
      )}

      {/* Grid */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-400">
            Memuat data…
          </div>
        ) : (
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50">
                <th className="border border-slate-200 px-3 py-2 text-left text-xs font-medium text-slate-500 w-28">
                  Sesi / Hari
                </th>
                {HARI_LIST.map((h) => (
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
                  {HARI_LIST.map((hari) => {
                    const ts = tsGrid[hari]?.[sesi]
                    return (
                      <TimeslotCell
                        key={hari}
                        timeslot={ts}
                        isUnavailable={ts ? localUnavail.has(ts.id) : false}
                        onToggle={() => ts && handleToggle(ts.id)}
                      />
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 text-[10px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="inline-flex items-center justify-center h-4 w-4 rounded bg-green-50 border border-green-200">
            <CheckCircle2 size={10} className="text-green-500" />
          </span>
          Tersedia — dapat dijadwalkan
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-flex items-center justify-center h-4 w-4 rounded bg-red-50 border border-red-200">
            <BanIcon size={10} className="text-red-500" />
          </span>
          Tidak Tersedia — tidak akan dijadwalkan
        </span>
      </div>

      {hasChanges && (
        <p className="text-xs text-amber-600">
          Ada perubahan yang belum disimpan. Klik <strong>Simpan</strong> untuk menyimpan.
        </p>
      )}
    </div>
  )
}
