import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { Badge } from '@/components/Badge'
import { useAuthStore } from '@/store/authStore'

import { getRuang, createRuang, updateRuang, Ruang, RuangCreatePayload, RuangJenis } from '@/api/ruang'

// ─── Constants ────────────────────────────────────────────────────────────────

const EDITOR_ROLES_JURUSAN = ['admin', 'sekretaris_jurusan', 'tendik_jurusan']

const JENIS_OPTIONS: RuangJenis[] = ['Kelas', 'Lab', 'Seminar']

const EMPTY_FORM: RuangCreatePayload = {
  nama: '',
  kapasitas: 45,
  lantai: null,
  gedung: null,
  jenis: 'Kelas',
  is_active: true,
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function RuangPage() {
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const canEdit = user ? EDITOR_ROLES_JURUSAN.includes(user.role) : false

  // ── Modal state ───────────────────────────────────────────────────────────
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Ruang | null>(null)
  const [form, setForm] = useState<RuangCreatePayload>(EMPTY_FORM)

  // ── Query ─────────────────────────────────────────────────────────────────
  const { data: ruangList = [], isLoading, isError } = useQuery({
    queryKey: ['ruang'],
    queryFn: getRuang,
  })

  // ── Mutations ─────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: createRuang,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ruang'] })
      closeModal()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: RuangCreatePayload }) =>
      updateRuang(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ruang'] })
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

  function openEdit(ruang: Ruang) {
    setEditTarget(ruang)
    setForm({
      nama: ruang.nama,
      kapasitas: ruang.kapasitas,
      lantai: ruang.lantai,
      gedung: ruang.gedung,
      jenis: ruang.jenis,
      is_active: ruang.is_active,
    })
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditTarget(null)
    setForm(EMPTY_FORM)
  }

  function handleSubmit() {
    const payload: RuangCreatePayload = {
      ...form,
      gedung: form.gedung || null,
      lantai: form.lantai ?? null,
    }
    if (editTarget) {
      updateMutation.mutate({ id: editTarget.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function setField<K extends keyof RuangCreatePayload>(key: K, value: RuangCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Columns ───────────────────────────────────────────────────────────────
  const columns: ColumnDef<Record<string, unknown>>[] = [
    { key: 'nama', label: 'Nama', sortable: true },
    { key: 'kapasitas', label: 'Kapasitas', sortable: true },
    {
      key: 'lantai',
      label: 'Lantai',
      render: (val) => (val != null ? String(val) : '—'),
    },
    {
      key: 'gedung',
      label: 'Gedung',
      render: (val) => (val ? String(val) : '—'),
    },
    { key: 'jenis', label: 'Jenis', sortable: true },
    {
      key: 'is_active',
      label: 'Status',
      sortable: true,
      render: (val) =>
        val ? (
          <Badge variant="Aktif">Aktif</Badge>
        ) : (
          <Badge variant="default">Non-Aktif</Badge>
        ),
    },
    ...(canEdit
      ? [
          {
            key: 'actions',
            label: '',
            render: (_: unknown, row: Record<string, unknown>) => (
              <button
                onClick={() => openEdit(row as unknown as Ruang)}
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
          <h1 className="text-base font-semibold text-slate-900">Daftar Ruang</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manajemen data ruang kuliah</p>
        </div>
        {canEdit && (
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            <Plus size={15} />
            Tambah Ruang
          </button>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data ruang. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={ruangList as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Tidak ada data ruang."
      />

      {/* Add / Edit Modal */}
      <FormModal
        open={modalOpen}
        onClose={closeModal}
        title={editTarget ? 'Edit Ruang' : 'Tambah Ruang'}
        onSubmit={handleSubmit}
        loading={isSaving}
      >
        <div className="grid grid-cols-2 gap-4">
          {/* Nama */}
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Nama <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.nama}
              onChange={(e) => setField('nama', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: R.101, LAB I"
            />
          </div>

          {/* Kapasitas */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Kapasitas</label>
            <input
              type="number"
              min={1}
              value={form.kapasitas ?? 45}
              onChange={(e) => setField('kapasitas', Number(e.target.value))}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            />
          </div>

          {/* Jenis */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Jenis</label>
            <select
              value={form.jenis ?? 'Kelas'}
              onChange={(e) => setField('jenis', e.target.value as RuangJenis)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {JENIS_OPTIONS.map((j) => (
                <option key={j} value={j}>{j}</option>
              ))}
            </select>
          </div>

          {/* Lantai */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Lantai</label>
            <input
              type="number"
              min={1}
              value={form.lantai ?? ''}
              onChange={(e) =>
                setField('lantai', e.target.value ? Number(e.target.value) : null)
              }
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Opsional"
            />
          </div>

          {/* Gedung */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Gedung</label>
            <input
              type="text"
              value={form.gedung ?? ''}
              onChange={(e) => setField('gedung', e.target.value || null)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Opsional"
            />
          </div>

          {/* is_active — only on edit */}
          {editTarget && (
            <div className="col-span-2 flex items-center gap-2">
              <input
                id="is_active"
                type="checkbox"
                checked={form.is_active ?? true}
                onChange={(e) => setField('is_active', e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
              />
              <label htmlFor="is_active" className="text-sm text-slate-700">
                Ruang aktif
              </label>
            </div>
          )}
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
