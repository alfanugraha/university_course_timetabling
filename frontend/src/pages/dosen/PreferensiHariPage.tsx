import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, Plus, Pencil, Trash2 } from 'lucide-react'

import { useAuthStore } from '@/store/authStore'
import { getTimeslots, Timeslot } from '@/api/timeslot'
import { getSesiList } from '@/api/sesi'
import {
  getDosen,
  getDosenPreferences,
  createDosenPreference,
  updateDosenPreference,
  deleteDosenPreference,
  DosenPreference,
  DosenPreferencePayload,
  PreferenceFase,
} from '@/api/dosen'
import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/Badge'

// ─── Constants ────────────────────────────────────────────────────────────────

const FASE_OPTIONS: { value: PreferenceFase; label: string }[] = [
  { value: 'pre_schedule', label: 'Pre-Schedule (Sebelum Jadwal Disusun)' },
  { value: 'post_draft', label: 'Post-Draft (Setelah Draft Dirilis)' },
]

const HARI_ORDER = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat']

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Group timeslots by hari for dropdown UX */
function groupTimeslotsByHari(timeslots: Timeslot[]): { hari: string; slots: Timeslot[] }[] {
  const map = new Map<string, Timeslot[]>()
  for (const ts of timeslots) {
    if (!map.has(ts.hari)) map.set(ts.hari, [])
    map.get(ts.hari)!.push(ts)
  }
  return HARI_ORDER.filter((h) => map.has(h)).map((h) => ({
    hari: h,
    slots: map.get(h)!.sort((a, b) => a.sesi - b.sesi),
  }))
}

// ─── Form State ───────────────────────────────────────────────────────────────

interface FormState {
  sesi_id: string
  timeslot_id: string
  fase: PreferenceFase
  catatan: string
}

const EMPTY_FORM: FormState = {
  sesi_id: '',
  timeslot_id: '',
  fase: 'pre_schedule',
  catatan: '',
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PreferensiHariPage() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  const [filterSesiId, setFilterSesiId] = useState<string>('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<DosenPreference | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DosenPreference | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  // ── Resolve dosen record ──────────────────────────────────────────────────

  const { data: dosenList = [], isLoading: dosenLoading } = useQuery({
    queryKey: ['dosen-all'],
    queryFn: () => getDosen(),
    enabled: !!user,
  })

  const myDosen = dosenList.find((d) => d.user_id === user?.id)
  const dosenId = myDosen?.id ?? null

  // ── Fetch sesi list ───────────────────────────────────────────────────────

  const { data: sesiList = [] } = useQuery({
    queryKey: ['sesi-list'],
    queryFn: getSesiList,
  })

  // ── Fetch timeslots ───────────────────────────────────────────────────────

  const { data: timeslots = [] } = useQuery({
    queryKey: ['timeslots'],
    queryFn: getTimeslots,
  })

  const timeslotGroups = groupTimeslotsByHari(timeslots)
  const timeslotMap = new Map(timeslots.map((ts) => [ts.id, ts]))

  // ── Fetch preferences ─────────────────────────────────────────────────────

  const {
    data: preferences = [],
    isLoading: prefLoading,
    isError: prefError,
  } = useQuery({
    queryKey: ['dosen-preferences', dosenId, filterSesiId],
    queryFn: () =>
      getDosenPreferences(dosenId!, filterSesiId ? { sesi_id: filterSesiId } : undefined),
    enabled: !!dosenId,
  })

  // ── Mutations ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (data: DosenPreferencePayload) => createDosenPreference(dosenId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen-preferences', dosenId] })
      closeModal()
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Gagal menyimpan preferensi'
      setFormError(msg)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DosenPreferencePayload> }) =>
      updateDosenPreference(dosenId!, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen-preferences', dosenId] })
      closeModal()
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Gagal memperbarui preferensi'
      setFormError(msg)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (prefId: string) => deleteDosenPreference(dosenId!, prefId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen-preferences', dosenId] })
      setDeleteTarget(null)
    },
  })

  // ── Modal helpers ─────────────────────────────────────────────────────────

  function openCreate() {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(pref: DosenPreference) {
    setEditTarget(pref)
    setForm({
      sesi_id: pref.sesi_id,
      timeslot_id: pref.timeslot_id,
      fase: pref.fase,
      catatan: pref.catatan ?? '',
    })
    setFormError(null)
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setFormError(null)
  }

  function handleSubmit() {
    if (!form.sesi_id || !form.timeslot_id) {
      setFormError('Sesi dan Timeslot wajib diisi.')
      return
    }
    const payload: DosenPreferencePayload = {
      sesi_id: form.sesi_id,
      timeslot_id: form.timeslot_id,
      fase: form.fase,
      catatan: form.catatan.trim() || null,
    }
    if (editTarget) {
      updateMutation.mutate({ id: editTarget.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const isMutating = createMutation.isPending || updateMutation.isPending

  // ── Table columns ─────────────────────────────────────────────────────────

  const sesiMap = new Map(sesiList.map((s) => [s.id, s]))

  const columns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: 'sesi_id',
      label: 'Sesi',
      render: (_val, row) => {
        const pref = row as unknown as DosenPreference
        const sesi = sesiMap.get(pref.sesi_id)
        return sesi ? (
          <span className="text-slate-700">{sesi.nama}</span>
        ) : (
          <span className="text-slate-400 italic">{pref.sesi_nama ?? pref.sesi_id}</span>
        )
      },
    },
    {
      key: 'timeslot_id',
      label: 'Timeslot',
      render: (_val, row) => {
        const pref = row as unknown as DosenPreference
        const ts = timeslotMap.get(pref.timeslot_id)
        return (
          <span className="text-slate-700">
            {ts ? ts.label : pref.timeslot_label ?? pref.timeslot_id}
          </span>
        )
      },
    },
    {
      key: 'fase',
      label: 'Fase',
      render: (_val, row) => {
        const pref = row as unknown as DosenPreference
        return (
          <Badge variant={pref.fase === 'pre_schedule' ? 'info' : 'default'} size="sm">
            {pref.fase === 'pre_schedule' ? 'Pre-Schedule' : 'Post-Draft'}
          </Badge>
        )
      },
    },
    {
      key: 'catatan',
      label: 'Catatan',
      render: (_val, row) => {
        const pref = row as unknown as DosenPreference
        return pref.catatan ? (
          <span className="text-slate-600 text-xs">{pref.catatan}</span>
        ) : (
          <span className="text-slate-300 text-xs italic">—</span>
        )
      },
    },
    {
      key: 'is_violated',
      label: 'Status',
      render: (_val, row) => {
        const pref = row as unknown as DosenPreference
        if (pref.is_violated) {
          return <Badge variant="ERROR" size="sm">Dilanggar</Badge>
        }
        return <Badge variant="success" size="sm">Dipenuhi</Badge>
      },
    },
    {
      key: 'id',
      label: 'Aksi',
      render: (_val, row) => {
        const pref = row as unknown as DosenPreference
        return (
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => openEdit(pref)}
              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
              title="Edit"
            >
              <Pencil size={14} />
            </button>
            <button
              type="button"
              onClick={() => setDeleteTarget(pref)}
              className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
              title="Hapus"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )
      },
    },
  ]

  const tableData = preferences as unknown as Record<string, unknown>[]

  // ── Render ────────────────────────────────────────────────────────────────

  const isLoading = dosenLoading || prefLoading

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <CalendarDays size={18} className="text-slate-500" />
          <div>
            <h1 className="text-base font-semibold text-slate-900">Preferensi Hari Mengajar</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Ajukan preferensi timeslot mengajar Anda per sesi jadwal
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={openCreate}
          disabled={!dosenId}
          className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Plus size={14} />
          Ajukan Preferensi
        </button>
      </div>

      {/* No dosen record warning */}
      {!dosenLoading && !myDosen && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Akun Anda belum terhubung ke data dosen. Hubungi administrator.
        </div>
      )}

      {/* Error loading preferences */}
      {prefError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data preferensi. Silakan coba lagi.
        </div>
      )}

      {/* Filter sesi */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-500 font-medium whitespace-nowrap">Filter Sesi:</label>
        <select
          value={filterSesiId}
          onChange={(e) => setFilterSesiId(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Sesi</option>
          {sesiList.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nama}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={tableData}
        loading={isLoading}
        emptyMessage="Belum ada preferensi yang diajukan. Klik 'Ajukan Preferensi' untuk menambahkan."
      />

      {/* Form Modal */}
      <FormModal
        open={modalOpen}
        onClose={closeModal}
        title={editTarget ? 'Edit Preferensi' : 'Ajukan Preferensi Hari Mengajar'}
        onSubmit={handleSubmit}
        submitLabel={editTarget ? 'Simpan Perubahan' : 'Ajukan'}
        loading={isMutating}
      >
        <div className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</div>
          )}

          {/* Sesi */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Sesi <span className="text-red-500">*</span>
            </label>
            <select
              value={form.sesi_id}
              onChange={(e) => setForm((f) => ({ ...f, sesi_id: e.target.value }))}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
              required
            >
              <option value="">Pilih sesi jadwal…</option>
              {sesiList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nama} ({s.semester} {s.tahun_akademik})
                </option>
              ))}
            </select>
          </div>

          {/* Fase */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Fase <span className="text-red-500">*</span>
            </label>
            <select
              value={form.fase}
              onChange={(e) => setForm((f) => ({ ...f, fase: e.target.value as PreferenceFase }))}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {FASE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Timeslot */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Timeslot <span className="text-red-500">*</span>
            </label>
            <select
              value={form.timeslot_id}
              onChange={(e) => setForm((f) => ({ ...f, timeslot_id: e.target.value }))}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
              required
            >
              <option value="">Pilih timeslot…</option>
              {timeslotGroups.map(({ hari, slots }) => (
                <optgroup key={hari} label={hari}>
                  {slots.map((ts) => (
                    <option key={ts.id} value={ts.id}>
                      {ts.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Catatan */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Catatan <span className="text-slate-400 font-normal">(opsional)</span>
            </label>
            <textarea
              value={form.catatan}
              onChange={(e) => setForm((f) => ({ ...f, catatan: e.target.value }))}
              rows={3}
              placeholder="Tambahkan catatan jika diperlukan…"
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
            />
          </div>
        </div>
      </FormModal>

      {/* Confirm Delete */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        title="Hapus Preferensi"
        message="Preferensi ini akan dihapus secara permanen. Lanjutkan?"
        confirmLabel="Hapus"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}
