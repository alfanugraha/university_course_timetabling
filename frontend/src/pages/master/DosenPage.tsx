import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { Badge } from '@/components/Badge'
import { useAuthStore } from '@/store/authStore'

import { getDosen, createDosen, updateDosen, Dosen, DosenCreatePayload } from '@/api/dosen'
import { getProdi, Prodi } from '@/api/prodi'

// ─── Status badge variant ─────────────────────────────────────────────────────

const STATUS_VARIANT: Record<string, string> = {
  Aktif: 'Aktif',       // green
  'Non-Aktif': 'default', // gray
  Pensiun: 'WARNING',   // orange/amber — reuses WARNING variant from Badge
}

const STATUS_OPTIONS = ['Aktif', 'Non-Aktif', 'Pensiun'] as const
type DosenStatus = (typeof STATUS_OPTIONS)[number]

// ─── Empty form state ─────────────────────────────────────────────────────────

const EMPTY_FORM: DosenCreatePayload = {
  kode: '',
  nama: '',
  nidn: '',
  nip: '',
  jabfung: '',
  kjfd: '',
  homebase_prodi_id: null,
  bkd_limit_sks: null,
  tgl_lahir: null,
  status: 'Aktif',
  user_id: null,
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function DosenPage() {
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  // ── Filters ──────────────────────────────────────────────────────────────
  const [filterStatus, setFilterStatus] = useState('')
  const [filterProdi, setFilterProdi] = useState('')

  // ── Modal state ───────────────────────────────────────────────────────────
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Dosen | null>(null)
  const [form, setForm] = useState<DosenCreatePayload>(EMPTY_FORM)

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: dosenList = [], isLoading, isError } = useQuery({
    queryKey: ['dosen', filterStatus, filterProdi],
    queryFn: () =>
      getDosen({
        status: filterStatus || undefined,
        homebase_prodi_id: filterProdi || undefined,
      }),
  })

  const { data: prodiList = [] } = useQuery<Prodi[]>({
    queryKey: ['prodi'],
    queryFn: getProdi,
  })

  // ── Mutations ─────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: createDosen,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen'] })
      closeModal()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: DosenCreatePayload }) =>
      updateDosen(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dosen'] })
      closeModal()
    },
  })

  const isSaving = createMutation.isPending || updateMutation.isPending

  // ── Handlers ──────────────────────────────────────────────────────────────
  function openAdd() {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setModalOpen(true)
  }

  function openEdit(dosen: Dosen) {
    setEditTarget(dosen)
    setForm({
      kode: dosen.kode,
      nama: dosen.nama,
      nidn: dosen.nidn ?? '',
      nip: dosen.nip ?? '',
      jabfung: dosen.jabfung ?? '',
      kjfd: dosen.kjfd ?? '',
      homebase_prodi_id: dosen.homebase_prodi_id ?? null,
      bkd_limit_sks: dosen.bkd_limit_sks ?? null,
      tgl_lahir: dosen.tgl_lahir ?? null,
      status: dosen.status,
      user_id: dosen.user_id ?? null,
    })
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditTarget(null)
    setForm(EMPTY_FORM)
  }

  function handleSubmit() {
    const payload: DosenCreatePayload = {
      ...form,
      nidn: form.nidn || null,
      nip: form.nip || null,
      jabfung: form.jabfung || null,
      kjfd: form.kjfd || null,
      homebase_prodi_id: form.homebase_prodi_id || null,
      tgl_lahir: form.tgl_lahir || null,
    }
    if (editTarget) {
      updateMutation.mutate({ id: editTarget.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function setField<K extends keyof DosenCreatePayload>(key: K, value: DosenCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Prodi lookup helper ───────────────────────────────────────────────────
  const prodiMap = Object.fromEntries(prodiList.map((p) => [p.id, p.singkat || p.nama]))

  // ── Columns ───────────────────────────────────────────────────────────────
  const columns: ColumnDef<Record<string, unknown>>[] = [
    { key: 'kode', label: 'Kode', sortable: true },
    { key: 'nama', label: 'Nama', sortable: true },
    {
      key: 'nidn',
      label: 'NIDN / NIP',
      render: (_, row) => {
        const d = row as unknown as Dosen
        return d.nidn || d.nip || '—'
      },
    },
    { key: 'jabfung', label: 'Jabfung', sortable: true },
    {
      key: 'homebase_prodi_id',
      label: 'Homebase',
      render: (val) => (val ? prodiMap[val as string] ?? '—' : '—'),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (val) => {
        const s = val as string
        return (
          <Badge variant={STATUS_VARIANT[s] ?? 'default'}>
            {s}
          </Badge>
        )
      },
    },
    ...(isAdmin
      ? [
          {
            key: 'actions',
            label: '',
            render: (_: unknown, row: Record<string, unknown>) => (
              <button
                onClick={() => openEdit(row as unknown as Dosen)}
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-slate-900">Daftar Dosen</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manajemen data dosen jurusan</p>
        </div>
        {isAdmin && (
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            <Plus size={15} />
            Tambah Dosen
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Status</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          value={filterProdi}
          onChange={(e) => setFilterProdi(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Homebase</option>
          {prodiList.map((p) => (
            <option key={p.id} value={p.id}>{p.singkat || p.nama}</option>
          ))}
        </select>

        {(filterStatus || filterProdi) && (
          <button
            onClick={() => { setFilterStatus(''); setFilterProdi('') }}
            className="text-xs text-slate-400 hover:text-slate-700 underline"
          >
            Reset filter
          </button>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data dosen. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={dosenList as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Tidak ada data dosen."
      />

      {/* Add / Edit Modal */}
      <FormModal
        open={modalOpen}
        onClose={closeModal}
        title={editTarget ? 'Edit Dosen' : 'Tambah Dosen'}
        onSubmit={handleSubmit}
        loading={isSaving}
        size="lg"
      >
        <div className="grid grid-cols-2 gap-4">
          {/* Kode */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Kode <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={form.kode}
              onChange={(e) => setField('kode', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: DSN001"
            />
          </div>

          {/* Nama */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Nama Lengkap <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={form.nama}
              onChange={(e) => setField('nama', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Nama dosen"
            />
          </div>

          {/* NIDN */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">NIDN</label>
            <input
              type="text"
              value={form.nidn ?? ''}
              onChange={(e) => setField('nidn', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Nomor Induk Dosen Nasional"
            />
          </div>

          {/* NIP */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">NIP</label>
            <input
              type="text"
              value={form.nip ?? ''}
              onChange={(e) => setField('nip', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Nomor Induk Pegawai"
            />
          </div>

          {/* Jabfung */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Jabatan Fungsional</label>
            <input
              type="text"
              value={form.jabfung ?? ''}
              onChange={(e) => setField('jabfung', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: Lektor Kepala"
            />
          </div>

          {/* KJFD */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">KJFD</label>
            <input
              type="text"
              value={form.kjfd ?? ''}
              onChange={(e) => setField('kjfd', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Kelompok Jabatan Fungsional Dosen"
            />
          </div>

          {/* Homebase Prodi */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Homebase Prodi</label>
            <select
              value={form.homebase_prodi_id ?? ''}
              onChange={(e) => setField('homebase_prodi_id', e.target.value || null)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              <option value="">— Pilih Prodi —</option>
              {prodiList.map((p) => (
                <option key={p.id} value={p.id}>{p.singkat || p.nama}</option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Status <span className="text-red-500">*</span></label>
            <select
              value={form.status ?? 'Aktif'}
              onChange={(e) => setField('status', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* BKD Limit SKS */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">BKD Limit SKS</label>
            <input
              type="number"
              min={0}
              value={form.bkd_limit_sks ?? ''}
              onChange={(e) => setField('bkd_limit_sks', e.target.value ? Number(e.target.value) : null)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Maks SKS per semester"
            />
          </div>

          {/* Tanggal Lahir */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Tanggal Lahir</label>
            <input
              type="date"
              value={form.tgl_lahir ?? ''}
              onChange={(e) => setField('tgl_lahir', e.target.value || null)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            />
          </div>
        </div>

        {/* Mutation error */}
        {(createMutation.isError || updateMutation.isError) && (
          <p className="mt-3 text-xs text-red-600">
            Gagal menyimpan data. Periksa kembali isian Anda.
          </p>
        )}
      </FormModal>
    </div>
  )
}
