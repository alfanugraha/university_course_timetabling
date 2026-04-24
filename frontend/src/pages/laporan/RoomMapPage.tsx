import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { getSesiList } from '@/api/sesi'
import { getRoomMap, type RoomCellInfo, type RoomMapSlot } from '@/api/report'

// ─── Cell component ───────────────────────────────────────────────────────────

function RoomCell({ info }: { info: RoomCellInfo | null }) {
  if (!info) {
    return <td className="border border-slate-200 bg-slate-50 w-24 h-10" />
  }
  return (
    <td className="border border-slate-200 bg-blue-50 w-24 h-10 px-1.5 py-1 align-top">
      <div className="text-[11px] font-semibold text-blue-800 leading-tight truncate" title={info.nama_mk}>
        {info.kode_mk}
        {info.kelas ? <span className="font-normal text-blue-600">/{info.kelas}</span> : null}
      </div>
      <div className="text-[10px] text-slate-500 truncate leading-tight" title={info.dosen}>
        {info.dosen}
      </div>
    </td>
  )
}

// ─── Grid grouped by day ──────────────────────────────────────────────────────

function RoomGrid({ slots, rooms }: { slots: RoomMapSlot[]; rooms: string[] }) {
  // Group slots by hari
  const grouped: Record<string, RoomMapSlot[]> = {}
  for (const slot of slots) {
    if (!grouped[slot.hari]) grouped[slot.hari] = []
    grouped[slot.hari].push(slot)
  }
  const days = Object.keys(grouped)

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="border-collapse text-sm min-w-max">
        <thead>
          <tr className="bg-slate-100">
            <th className="border border-slate-200 px-3 py-2 text-left text-xs font-semibold text-slate-600 whitespace-nowrap sticky left-0 bg-slate-100 z-10 min-w-[110px]">
              Hari / Sesi
            </th>
            {rooms.map((room) => (
              <th
                key={room}
                className="border border-slate-200 px-2 py-2 text-center text-xs font-semibold text-slate-600 whitespace-nowrap w-24"
              >
                {room}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {days.map((hari) => {
            const daySlots = grouped[hari]
            return daySlots.map((slot, idx) => (
              <tr key={`${hari}-${slot.sesi}`} className="hover:bg-slate-50/50">
                {idx === 0 ? (
                  <td
                    rowSpan={daySlots.length}
                    className="border border-slate-200 px-3 py-2 align-middle text-xs font-semibold text-slate-700 bg-slate-50 sticky left-0 z-10 whitespace-nowrap"
                  >
                    {hari}
                  </td>
                ) : null}
                <td className="border border-slate-200 px-2 py-1 text-xs text-slate-500 whitespace-nowrap bg-white min-w-[80px]">
                  {slot.label}
                </td>
                {rooms.map((room) => (
                  <RoomCell key={room} info={slot.rooms[room] ?? null} />
                ))}
              </tr>
            ))
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RoomMapPage() {
  const [sesiId, setSesiId] = useState<string>('')

  const { data: sesiList = [], isLoading: sesiLoading } = useQuery({
    queryKey: ['sesi-list'],
    queryFn: getSesiList,
  })

  const { data: roomMap, isLoading: mapLoading, error } = useQuery({
    queryKey: ['room-map', sesiId],
    queryFn: () => getRoomMap(sesiId),
    enabled: !!sesiId,
  })

  // Count occupied cells for summary
  const occupiedCount = roomMap
    ? roomMap.slots.reduce(
        (acc, slot) => acc + Object.values(slot.rooms).filter(Boolean).length,
        0
      )
    : 0
  const totalCells = roomMap ? roomMap.slots.length * roomMap.rooms.length : 0

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Peta Penggunaan Ruang</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Matrix hari × sesi × ruang — sel berwarna menunjukkan ruang terpakai.
        </p>
      </div>

      {/* Sesi selector */}
      <div className="flex items-center gap-3 flex-wrap">
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
        {roomMap && (
          <span className="text-xs text-slate-400">
            {occupiedCount} dari {totalCells} slot terisi
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Gagal memuat peta ruang. Coba lagi.
        </div>
      )}

      {/* Prompt state */}
      {!sesiId && !mapLoading && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-slate-400">
          Pilih sesi jadwal untuk melihat peta penggunaan ruang.
        </div>
      )}

      {/* Loading */}
      {sesiId && mapLoading && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-slate-400">
          Memuat data…
        </div>
      )}

      {/* Grid */}
      {roomMap && !mapLoading && (
        <RoomGrid slots={roomMap.slots} rooms={roomMap.rooms} />
      )}

      {/* Legend */}
      {roomMap && (
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="font-medium">Keterangan:</span>
          <span className="flex items-center gap-1.5">
            <span className={cn('inline-block w-4 h-4 rounded-sm bg-blue-50 border border-blue-200')} />
            Terpakai
          </span>
          <span className="flex items-center gap-1.5">
            <span className={cn('inline-block w-4 h-4 rounded-sm bg-slate-50 border border-slate-200')} />
            Kosong
          </span>
        </div>
      )}
    </div>
  )
}
