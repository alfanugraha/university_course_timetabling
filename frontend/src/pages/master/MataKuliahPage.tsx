import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, ChevronRight, ArrowLeft, BookOpen } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/Badge'
import { useAuthStore } from '@/store/authStore'
import { getProdi, Prodi } from '@/api/prodi'
import {
  getMataKuliah,
  createMataKuliah,
  updateMataKuliah,
  deleteMataKuliah,
  getKelas,
  createKelas,
  updateKelas,
  deleteKelas,
  getKurikulum,
  MataKuliah,
  MataKuliahKelas,
  MataKuliahCreatePayload,
  MataKuliahKelasPayload,
  Kurikulum,
} from '@/api/mataKuliah'

// ─── Constants ────────────────────────────────────────────────────────────────

const JENIS_OPTIONS = ['Wajib', 'Pilihan'] as const
const SEMESTER_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8] as const

const EDITOR_ROLES = ['admin', 'sekretaris_jurusan', 'tendik_jurusan']

const EMPTY_MK_FORM: MataKuliahCreatePayload = {
  kode: '',
  kurikulum_id: '',
  nama: '',
  sks: 3,
  semester: 1,
  jenis: 'Wajib',
  prasyarat: null,
}

const EMPTY_KELAS_FORM: MataKuliahKelasPayload = {
  kelas: null,
  label: '',
  ket: null,
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function MataKuliahPage() {
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const canEdit = EDITOR_ROLES.includes(user?.role ?? '')

  // ── View state: null = list, string = kelas sub-page for that MK ──────────
  const [selectedMk, setSelectedMk] = useState<MataKuliah | null>(null)

  if (selectedMk) {
    return (
      <KelasSubPage
        mk={selectedMk}
        canEdit={canEdit}
        onBack={() => setSelectedMk(null)}
      />
    )
  }

  return (
    <MataKuliahList
      canEdit={canEdit}
      onOpenKelas={(mk) => setSelectedMk(mk)}
    />
  )
}

// ─── Mata Kuliah List ─────────────────────────────────────────────────────────

function MataKuliahList({
  canEdit,
  onOpenKelas,
}: {
  canEdit: boolean
  onOpenKelas: (mk: MataKuliah) => void
}) {
  const queryClient = useQueryClient()

  // ── Filters ───────────────────────────────────────────────────────────────
  const [filterProdi, setFilterProdi] = useState('')
  const [filterKurikulum, setFilterKurikulum] = useState('')
  const [filterSemester, setFilterSemester] = useState('')

  // ── Modal state ───────────────────────────────────────────────────────────
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<MataKuliah | null>(null)
  const [form, setForm] = useState<MataKuliahCreatePayload>(EMPTY_MK_FORM)

  // ── Delete confirm ────────────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<MataKuliah | null>(null)

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: mkList = [], isLoading, isError } = useQuery({
    queryKey: ['mata-kuliah', filterProdi, filterKurikulum, filterSemester],
    queryFn: () =>
      getMataKuliah({
        prodi_id: filterProdi || undefined,
        kurikulum_id: filterKurikulum || undefined,
        semester: filterSemester ? Number(filterSemester) : undefined,
      }),
  })

  const { data: prodiList = [] } = useQuery<Prodi[]>({
    queryKey: ['prodi'],
    queryFn: getProdi,
  })

  const { data: kurikulumList = [] } = useQuery<Kurikulum[]>({
    queryKey: ['kurikulum'],
    queryFn: getKurikulum,
  })

  // ── Mutations ─────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: createMataKuliah,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mata-kuliah'] })
      closeModal()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MataKuliahCreatePayload> }) =>
      updateMataKuliah(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mata-kuliah'] })
      closeModal()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteMataKuliah,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mata-kuliah'] })
      setDeleteTarget(null)
    },
  })

  const isSaving = createMutation.isPending || updateMutation.isPending

  // ── Handlers ──────────────────────────────────────────────────────────────
  function openAdd() {
    setEditTarget(null)
    setForm(EMPTY_MK_FORM)
    setModalOpen(true)
  }

  function openEdit(mk: MataKuliah) {
    setEditTarget(mk)
    setForm({
      kode: mk.kode,
      kurikulum_id: mk.kurikulum_id,
      nama: mk.nama,
      sks: mk.sks,
      semester: mk.semester,
      jenis: mk.jenis,
      prasyarat: mk.prasyarat,
    })
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditTarget(null)
    setForm(EMPTY_MK_FORM)
  }

  function handleSubmit() {
    const payload = { ...form, prasyarat: form.prasyarat || null }
    if (editTarget) {
      updateMutation.mutate({ id: editTarget.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function setField<K extends keyof MataKuliahCreatePayload>(
    key: K,
    value: MataKuliahCreatePayload[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Lookup maps ───────────────────────────────────────────────────────────
  const prodiMap = Object.fromEntries(prodiList.map((p) => [p.id, p.singkat || p.nama]))
  const filteredKurikulum = filterProdi
    ? kurikulumList.filter((k) => k.prodi_id === filterProdi)
    : kurikulumList

  // ── Columns ───────────────────────────────────────────────────────────────
  const columns: ColumnDef<Record<string, unknown>>[] = [
    { key: 'kode', label: 'Kode', sortable: true },
    { key: 'nama', label: 'Nama Mata Kuliah', sortable: true },
    { key: 'sks', label: 'SKS', sortable: true },
    { key: 'semester', label: 'Smt', sortable: true },
    {
      key: 'jenis',
      label: 'Jenis',
      render: (val) => (
        <Badge variant={val === 'Wajib' ? 'Aktif' : 'default'}>{val as string}</Badge>
      ),
    },
    {
      key: 'kurikulum',
      label: 'Kurikulum',
      render: (_, row) => {
        const mk = row as unknown as MataKuliah
        if (!mk.kurikulum) return '—'
        const prodi = prodiMap[mk.kurikulum.prodi_id] ?? '?'
        return `${mk.kurikulum.kode} (${prodi})`
      },
    },
    {
      key: 'actions',
      label: '',
      render: (_, row) => {
        const mk = row as unknown as MataKuliah
        return (
          <div className="flex items-center gap-1">
            <button
              onClick={() => onOpenKelas(mk)}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
              title="Lihat kelas paralel"
            >
              <BookOpen size={13} />
              Kelas
              <ChevronRight size={12} />
            </button>
            {canEdit && (
              <>
                <button
                  onClick={() => openEdit(mk)}
                  className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                >
                  <Pencil size={13} />
                  Edit
                </button>
                <button
                  onClick={() => setDeleteTarget(mk)}
                  className="flex items-center gap-1 rounded px-2 py-1 text-xs text-red-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 size={13} />
                </button>
              </>
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-slate-900">Daftar Mata Kuliah</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manajemen mata kuliah dan kelas paralel</p>
        </div>
        {canEdit && (
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            <Plus size={15} />
            Tambah MK
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterProdi}
          onChange={(e) => {
            setFilterProdi(e.target.value)
            setFilterKurikulum('')
          }}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Prodi</option>
          {prodiList.map((p) => (
            <option key={p.id} value={p.id}>{p.singkat || p.nama}</option>
          ))}
        </select>

        <select
          value={filterKurikulum}
          onChange={(e) => setFilterKurikulum(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Kurikulum</option>
          {filteredKurikulum.map((k) => (
            <option key={k.id} value={k.id}>{k.kode} ({k.tahun})</option>
          ))}
        </select>

        <select
          value={filterSemester}
          onChange={(e) => setFilterSemester(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">Semua Semester</option>
          {SEMESTER_OPTIONS.map((s) => (
            <option key={s} value={s}>Semester {s}</option>
          ))}
        </select>

        {(filterProdi || filterKurikulum || filterSemester) && (
          <button
            onClick={() => {
              setFilterProdi('')
              setFilterKurikulum('')
              setFilterSemester('')
            }}
            className="text-xs text-slate-400 hover:text-slate-700 underline"
          >
            Reset filter
          </button>
        )}
      </div>

      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data mata kuliah. Silakan coba lagi.
        </div>
      )}

      <DataTable
        columns={columns}
        data={mkList as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Tidak ada data mata kuliah."
      />

      {/* Add / Edit Modal */}
      <FormModal
        open={modalOpen}
        onClose={closeModal}
        title={editTarget ? 'Edit Mata Kuliah' : 'Tambah Mata Kuliah'}
        onSubmit={handleSubmit}
        loading={isSaving}
        size="lg"
      >
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Kode <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.kode}
              onChange={(e) => setField('kode', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: MAT101"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Kurikulum <span className="text-red-500">*</span>
            </label>
            <select
              value={form.kurikulum_id}
              onChange={(e) => setField('kurikulum_id', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              <option value="">— Pilih Kurikulum —</option>
              {kurikulumList.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.kode} ({k.tahun})
                </option>
              ))}
            </select>
          </div>

          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Nama Mata Kuliah <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.nama}
              onChange={(e) => setField('nama', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Nama lengkap mata kuliah"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              SKS <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min={1}
              max={6}
              value={form.sks}
              onChange={(e) => setField('sks', Number(e.target.value))}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Semester <span className="text-red-500">*</span>
            </label>
            <select
              value={form.semester}
              onChange={(e) => setField('semester', Number(e.target.value))}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {SEMESTER_OPTIONS.map((s) => (
                <option key={s} value={s}>Semester {s}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Jenis <span className="text-red-500">*</span>
            </label>
            <select
              value={form.jenis}
              onChange={(e) => setField('jenis', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {JENIS_OPTIONS.map((j) => (
                <option key={j} value={j}>{j}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Prasyarat</label>
            <input
              type="text"
              value={form.prasyarat ?? ''}
              onChange={(e) => setField('prasyarat', e.target.value || null)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Kode MK prasyarat (opsional)"
            />
          </div>
        </div>

        {(createMutation.isError || updateMutation.isError) && (
          <p className="mt-3 text-xs text-red-600">
            Gagal menyimpan data. Periksa kembali isian Anda.
          </p>
        )}
      </FormModal>

      {/* Delete Confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        title="Hapus Mata Kuliah"
        message={`Mata kuliah "${deleteTarget?.nama}" akan dinonaktifkan. Tindakan ini tidak dapat dibatalkan.`}
        confirmLabel="Hapus"
        loading={deleteMutation.isPending}
        variant="danger"
      />
    </div>
  )
}

// ─── Kelas Sub-Page ───────────────────────────────────────────────────────────

function KelasSubPage({
  mk,
  canEdit,
  onBack,
}: {
  mk: MataKuliah
  canEdit: boolean
  onBack: () => void
}) {
  const queryClient = useQueryClient()

  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<MataKuliahKelas | null>(null)
  const [form, setForm] = useState<MataKuliahKelasPayload>(EMPTY_KELAS_FORM)
  const [deleteTarget, setDeleteTarget] = useState<MataKuliahKelas | null>(null)

  const { data: kelasList = [], isLoading, isError } = useQuery({
    queryKey: ['kelas', mk.id],
    queryFn: () => getKelas(mk.id),
  })

  const createMutation = useMutation({
    mutationFn: (data: MataKuliahKelasPayload) => createKelas(mk.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kelas', mk.id] })
      closeModal()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MataKuliahKelasPayload> }) =>
      updateKelas(mk.id, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kelas', mk.id] })
      closeModal()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (kelasId: string) => deleteKelas(mk.id, kelasId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kelas', mk.id] })
      setDeleteTarget(null)
    },
  })

  const isSaving = createMutation.isPending || updateMutation.isPending

  function openAdd() {
    setEditTarget(null)
    setForm(EMPTY_KELAS_FORM)
    setModalOpen(true)
  }

  function openEdit(kelas: MataKuliahKelas) {
    setEditTarget(kelas)
    setForm({ kelas: kelas.kelas, label: kelas.label, ket: kelas.ket })
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditTarget(null)
    setForm(EMPTY_KELAS_FORM)
  }

  function handleSubmit() {
    const payload = { ...form, ket: form.ket || null }
    if (editTarget) {
      updateMutation.mutate({ id: editTarget.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function setField<K extends keyof MataKuliahKelasPayload>(
    key: K,
    value: MataKuliahKelasPayload[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const columns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: 'kelas',
      label: 'Kelas',
      sortable: true,
      render: (val) => (val ? <span className="font-medium">{val as string}</span> : <span className="text-slate-400 italic">Tunggal</span>),
    },
    { key: 'label', label: 'Label', sortable: true },
    { key: 'ket', label: 'Keterangan', render: (val) => (val as string) || '—' },
    ...(canEdit
      ? [
          {
            key: 'actions',
            label: '',
            render: (_: unknown, row: Record<string, unknown>) => {
              const k = row as unknown as MataKuliahKelas
              return (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => openEdit(k)}
                    className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                  >
                    <Pencil size={13} />
                    Edit
                  </button>
                  <button
                    onClick={() => setDeleteTarget(k)}
                    className="flex items-center gap-1 rounded px-2 py-1 text-xs text-red-400 hover:bg-red-50 hover:text-red-600"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              )
            },
          } as ColumnDef<Record<string, unknown>>,
        ]
      : []),
  ]

  return (
    <div className="space-y-4">
      {/* Breadcrumb / back */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <button
          onClick={onBack}
          className="flex items-center gap-1 hover:text-slate-800"
        >
          <ArrowLeft size={14} />
          Mata Kuliah
        </button>
        <ChevronRight size={14} />
        <span className="text-slate-800 font-medium">{mk.kode} — {mk.nama}</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-slate-900">Kelas Paralel</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {mk.kode} · {mk.nama} · {mk.sks} SKS · Semester {mk.semester}
          </p>
        </div>
        {canEdit && (
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            <Plus size={15} />
            Tambah Kelas
          </button>
        )}
      </div>

      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data kelas. Silakan coba lagi.
        </div>
      )}

      <DataTable
        columns={columns}
        data={kelasList as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Belum ada kelas paralel untuk mata kuliah ini."
      />

      {/* Add / Edit Kelas Modal */}
      <FormModal
        open={modalOpen}
        onClose={closeModal}
        title={editTarget ? 'Edit Kelas' : 'Tambah Kelas Paralel'}
        onSubmit={handleSubmit}
        loading={isSaving}
        size="md"
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Kelas</label>
            <input
              type="text"
              value={form.kelas ?? ''}
              onChange={(e) => setField('kelas', e.target.value || null)}
              maxLength={5}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: A, B, C (kosongkan jika tunggal)"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Label <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.label}
              onChange={(e) => setField('label', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: Kalkulus I (MTK25) - A"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Keterangan</label>
            <textarea
              value={form.ket ?? ''}
              onChange={(e) => setField('ket', e.target.value || null)}
              rows={2}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
              placeholder="Keterangan tambahan (opsional)"
            />
          </div>
        </div>

        {(createMutation.isError || updateMutation.isError) && (
          <p className="mt-3 text-xs text-red-600">
            Gagal menyimpan data. Periksa kembali isian Anda.
          </p>
        )}
      </FormModal>

      {/* Delete Confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        title="Hapus Kelas"
        message={`Kelas "${deleteTarget?.label}" akan dihapus permanen.`}
        confirmLabel="Hapus"
        loading={deleteMutation.isPending}
        variant="danger"
      />
    </div>
  )
}
