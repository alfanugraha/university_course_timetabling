import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Pencil } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { useAuthStore } from '@/store/authStore'

import {
  getTimeslots,
  updateTimeslot,
  Timeslot,
  TimeslotUpdatePayload,
  HariOption,
} from '@/api/timeslot'

// ─── Constants ────────────────────────────────────────────────────────────────

const HARI_OPTIONS: HariOption[] = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat']
const SESI_OPTIONS = [1, 2, 3]

// ─── Component ────────────────────────────────────────────────────────────────

export default function TimeslotPage() {
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  // ── Modal state ───────────────────────────────────────────────────────────
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Timeslot | null>(null)
  const [form, setForm] = useState<TimeslotUpdatePayload>({})

  // ── Query ─────────────────────────────────────────────────────────────────
  const { data: timeslots = [], isLoading, isError } = useQuery({
    queryKey: ['timeslots'],
    queryFn: getTimeslots,
  })

  // ── Mutation ──────────────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TimeslotUpdatePayload }) =>
      updateTimeslot(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timeslots'] })
      closeModal()
    },
  })

  // ── Handlers ──────────────────────────────────────────────────────────────
  function openEdit(ts: Timeslot) {
    setEditTarget(ts)
    setForm({
      kode: ts.kode,
      hari: ts.hari,
      sesi: ts.sesi,
      jam_mulai: ts.jam_mulai,
      jam_selesai: ts.jam_selesai,
      label: ts.label,
      sks: ts.sks,
    })
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditTarget(null)
    setForm({})
  }

  function handleSubmit() {
    if (!editTarget) return
    updateMutation.mutate({ id: editTarget.id, data: form })
  }

  function setField<K extends keyof TimeslotUpdatePayload>(
    key: K,
    value: TimeslotUpdatePayload[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Columns ───────────────────────────────────────────────────────────────
  const columns: ColumnDef<Record<string, unknown>>[] = [
    { key: 'kode', label: 'Kode', sortable: true },
    { key: 'hari', label: 'Hari', sortable: true },
    { key: 'sesi', label: 'Sesi', sortable: true },
    { key: 'jam_mulai', label: 'Jam Mulai' },
    { key: 'jam_selesai', label: 'Jam Selesai' },
    { key: 'label', label: 'Label' },
    { key: 'sks', label: 'SKS', sortable: true },
    ...(isAdmin
      ? [
          {
            key: 'actions',
            label: '',
            render: (_: unknown, row: Record<string, unknown>) => (
              <button
                onClick={() => openEdit(row as unknown as Timeslot)}
                className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              >
                <Pencil size={13} />
                Edit
              </button>
            ),
          } as ColumnDef<Record<string, unknown>>,
        ]
      : []),
  ]

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* Page header */}
      <div>
        <h1 className="text-base font-semibold text-slate-900">Daftar Timeslot</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          15 slot waktu tetap — Senin s.d. Jumat, 3 sesi per hari
        </p>
      </div>

      {/* Error state */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data timeslot. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={timeslots as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Tidak ada data timeslot."
        pageSize={15}
      />

      {/* Edit Modal — admin only */}
      {isAdmin && (
        <FormModal
          open={modalOpen}
          onClose={closeModal}
          title="Edit Timeslot"
          onSubmit={handleSubmit}
          loading={updateMutation.isPending}
        >
          <div className="grid grid-cols-2 gap-4">
            {/* Kode */}
            <div className="col-span-2 flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">Kode</label>
              <input
                type="text"
                value={form.kode ?? ''}
                onChange={(e) => setField('kode', e.target.value)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
                placeholder="Contoh: mon_s1"
              />
            </div>

            {/* Hari */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">Hari</label>
              <select
                value={form.hari ?? ''}
                onChange={(e) => setField('hari', e.target.value)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              >
                {HARI_OPTIONS.map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
            </div>

            {/* Sesi */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">Sesi</label>
              <select
                value={form.sesi ?? 1}
                onChange={(e) => setField('sesi', Number(e.target.value))}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              >
                {SESI_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Jam Mulai */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">Jam Mulai</label>
              <input
                type="time"
                value={form.jam_mulai ?? ''}
                onChange={(e) => setField('jam_mulai', e.target.value)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              />
            </div>

            {/* Jam Selesai */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">Jam Selesai</label>
              <input
                type="time"
                value={form.jam_selesai ?? ''}
                onChange={(e) => setField('jam_selesai', e.target.value)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              />
            </div>

            {/* Label */}
            <div className="col-span-2 flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">Label</label>
              <input
                type="text"
                value={form.label ?? ''}
                onChange={(e) => setField('label', e.target.value)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
                placeholder="Contoh: Senin Sesi 1"
              />
            </div>

            {/* SKS */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-700">SKS</label>
              <input
                type="number"
                min={1}
                max={6}
                value={form.sks ?? 3}
                onChange={(e) => setField('sks', Number(e.target.value))}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              />
            </div>
          </div>

          {updateMutation.isError && (
            <p className="mt-3 text-xs text-red-600">
              Gagal menyimpan data. Periksa kembali isian Anda.
            </p>
          )}
        </FormModal>
      )}
    </div>
  )
}
