import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, ChevronDown, ChevronRight } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { Badge } from '@/components/Badge'
import { useAuthStore } from '@/store/authStore'

import { getProdi, createProdi, updateProdi, Prodi, ProdiCreatePayload } from '@/api/prodi'
import { getKurikulum, createKurikulum, updateKurikulum, Kurikulum, KurikulumCreatePayload } from '@/api/kurikulum'

// ─── Constants ────────────────────────────────────────────────────────────────

const STRATA_OPTIONS = ['S1', 'S2', 'S3', 'D3', 'D4'] as const
const KATEGORI_OPTIONS = ['Reguler', 'Internasional', 'Kelas Karyawan'] as const

const EMPTY_PRODI_FORM: ProdiCreatePayload = {
  kode: '',
  strata: 'S1',
  nama: '',
  singkat: '',
  kategori: 'Reguler',
  is_active: true,
}

const EMPTY_KURIKULUM_FORM: KurikulumCreatePayload = {
  kode: '',
  tahun: '',
  prodi_id: '',
  is_active: true,
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ProdiPage() {
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  // ── Expanded prodi row ────────────────────────────────────────────────────
  const [expandedProdiId, setExpandedProdiId] = useState<string | null>(null)

  // ── Prodi modal state ─────────────────────────────────────────────────────
  const [prodiModalOpen, setProdiModalOpen] = useState(false)
  const [editProdi, setEditProdi] = useState<Prodi | null>(null)
  const [prodiForm, setProdiForm] = useState<ProdiCreatePayload>(EMPTY_PRODI_FORM)

  // ── Kurikulum modal state ─────────────────────────────────────────────────
  const [kurikulumModalOpen, setKurikulumModalOpen] = useState(false)
  const [editKurikulum, setEditKurikulum] = useState<Kurikulum | null>(null)
  const [kurikulumForm, setKurikulumForm] = useState<KurikulumCreatePayload>(EMPTY_KURIKULUM_FORM)

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: prodiList = [], isLoading: prodiLoading, isError: prodiError } = useQuery({
    queryKey: ['prodi'],
    queryFn: getProdi,
  })

  const { data: kurikulumList = [] } = useQuery({
    queryKey: ['kurikulum'],
    queryFn: getKurikulum,
  })

  // ── Prodi mutations ───────────────────────────────────────────────────────
  const createProdiMutation = useMutation({
    mutationFn: createProdi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prodi'] })
      closeProdiModal()
    },
  })

  const updateProdiMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProdiCreatePayload> }) =>
      updateProdi(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prodi'] })
      closeProdiModal()
    },
  })

  // ── Kurikulum mutations ───────────────────────────────────────────────────
  const createKurikulumMutation = useMutation({
    mutationFn: createKurikulum,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kurikulum'] })
      closeKurikulumModal()
    },
  })

  const updateKurikulumMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<KurikulumCreatePayload> }) =>
      updateKurikulum(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kurikulum'] })
      closeKurikulumModal()
    },
  })

  const isProdiSaving = createProdiMutation.isPending || updateProdiMutation.isPending
  const isKurikulumSaving = createKurikulumMutation.isPending || updateKurikulumMutation.isPending

  // ── Prodi handlers ────────────────────────────────────────────────────────
  function openAddProdi() {
    setEditProdi(null)
    setProdiForm(EMPTY_PRODI_FORM)
    setProdiModalOpen(true)
  }

  function openEditProdi(prodi: Prodi) {
    setEditProdi(prodi)
    setProdiForm({
      kode: prodi.kode,
      strata: prodi.strata,
      nama: prodi.nama,
      singkat: prodi.singkat,
      kategori: prodi.kategori,
      is_active: prodi.is_active,
    })
    setProdiModalOpen(true)
  }

  function closeProdiModal() {
    setProdiModalOpen(false)
    setEditProdi(null)
    setProdiForm(EMPTY_PRODI_FORM)
  }

  function handleProdiSubmit() {
    if (editProdi) {
      updateProdiMutation.mutate({ id: editProdi.id, data: prodiForm })
    } else {
      createProdiMutation.mutate(prodiForm)
    }
  }

  function setProdiField<K extends keyof ProdiCreatePayload>(key: K, value: ProdiCreatePayload[K]) {
    setProdiForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Kurikulum handlers ────────────────────────────────────────────────────
  function openAddKurikulum(prodiId: string) {
    setEditKurikulum(null)
    setKurikulumForm({ ...EMPTY_KURIKULUM_FORM, prodi_id: prodiId })
    setKurikulumModalOpen(true)
  }

  function openEditKurikulum(k: Kurikulum) {
    setEditKurikulum(k)
    setKurikulumForm({
      kode: k.kode,
      tahun: k.tahun,
      prodi_id: k.prodi_id,
      is_active: k.is_active,
    })
    setKurikulumModalOpen(true)
  }

  function closeKurikulumModal() {
    setKurikulumModalOpen(false)
    setEditKurikulum(null)
    setKurikulumForm(EMPTY_KURIKULUM_FORM)
  }

  function handleKurikulumSubmit() {
    if (editKurikulum) {
      updateKurikulumMutation.mutate({ id: editKurikulum.id, data: kurikulumForm })
    } else {
      createKurikulumMutation.mutate(kurikulumForm)
    }
  }

  function setKurikulumField<K extends keyof KurikulumCreatePayload>(key: K, value: KurikulumCreatePayload[K]) {
    setKurikulumForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Prodi columns ─────────────────────────────────────────────────────────
  const prodiColumns: ColumnDef<Record<string, unknown>>[] = [
    {
      key: 'expand',
      label: '',
      render: (_, row) => {
        const prodi = row as unknown as Prodi
        const isExpanded = expandedProdiId === prodi.id
        return (
          <button
            onClick={() => setExpandedProdiId(isExpanded ? null : prodi.id)}
            className="flex items-center justify-center rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label={isExpanded ? 'Tutup kurikulum' : 'Lihat kurikulum'}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )
      },
    },
    { key: 'kode', label: 'Kode', sortable: true },
    { key: 'nama', label: 'Nama', sortable: true },
    { key: 'strata', label: 'Strata', sortable: true },
    { key: 'singkat', label: 'Singkat', sortable: true },
    { key: 'kategori', label: 'Kategori', sortable: true },
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
    ...(isAdmin
      ? [
          {
            key: 'actions',
            label: '',
            render: (_: unknown, row: Record<string, unknown>) => (
              <button
                onClick={() => openEditProdi(row as unknown as Prodi)}
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

  // ── Kurikulum columns ─────────────────────────────────────────────────────
  function getKurikulumColumns(_prodiId: string): ColumnDef<Record<string, unknown>>[] {
    return [
      { key: 'kode', label: 'Kode', sortable: true },
      { key: 'tahun', label: 'Tahun', sortable: true },
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
      ...(isAdmin
        ? [
            {
              key: 'actions',
              label: '',
              render: (_: unknown, row: Record<string, unknown>) => (
                <button
                  onClick={() => openEditKurikulum(row as unknown as Kurikulum)}
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
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-slate-900">Prodi &amp; Kurikulum</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manajemen program studi dan kurikulum</p>
        </div>
        {isAdmin && (
          <button
            onClick={openAddProdi}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            <Plus size={15} />
            Tambah Prodi
          </button>
        )}
      </div>

      {/* Error state */}
      {prodiError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data prodi. Silakan coba lagi.
        </div>
      )}

      {/* Prodi table with expandable kurikulum rows */}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              {prodiColumns.map((col) => (
                <th
                  key={String(col.key)}
                  className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {prodiLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  {prodiColumns.map((col) => (
                    <td key={String(col.key)} className="px-4 py-3">
                      <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
                    </td>
                  ))}
                </tr>
              ))
            ) : prodiList.length === 0 ? (
              <tr>
                <td colSpan={prodiColumns.length} className="px-4 py-10 text-center text-sm text-slate-400">
                  Tidak ada data prodi.
                </td>
              </tr>
            ) : (
              prodiList.map((prodi) => {
                const isExpanded = expandedProdiId === prodi.id
                const prodiKurikulum = kurikulumList.filter((k) => k.prodi_id === prodi.id)
                const row = prodi as unknown as Record<string, unknown>

                return (
                  <>
                    <tr key={prodi.id} className="hover:bg-slate-50">
                      {prodiColumns.map((col) => {
                        const key = String(col.key)
                        const raw = row[key]
                        return (
                          <td key={key} className="px-4 py-2.5 text-slate-700">
                            {col.render ? col.render(raw, row) : (raw as React.ReactNode) ?? '—'}
                          </td>
                        )
                      })}
                    </tr>

                    {isExpanded && (
                      <tr key={`${prodi.id}-kurikulum`}>
                        <td colSpan={prodiColumns.length} className="bg-slate-50 px-6 py-4">
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                                Kurikulum — {prodi.singkat || prodi.nama}
                              </p>
                              {isAdmin && (
                                <button
                                  onClick={() => openAddKurikulum(prodi.id)}
                                  className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                                >
                                  <Plus size={12} />
                                  Tambah Kurikulum
                                </button>
                              )}
                            </div>

                            <DataTable
                              columns={getKurikulumColumns(prodi.id)}
                              data={prodiKurikulum as unknown as Record<string, unknown>[]}
                              loading={false}
                              emptyMessage="Belum ada kurikulum untuk prodi ini."
                              pageSize={10}
                            />
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── Prodi Modal ── */}
      <FormModal
        open={prodiModalOpen}
        onClose={closeProdiModal}
        title={editProdi ? 'Edit Prodi' : 'Tambah Prodi'}
        onSubmit={handleProdiSubmit}
        loading={isProdiSaving}
      >
        <div className="grid grid-cols-2 gap-4">
          {/* Kode */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Kode <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={prodiForm.kode}
              onChange={(e) => setProdiField('kode', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: MTK"
            />
          </div>

          {/* Strata */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Strata <span className="text-red-500">*</span>
            </label>
            <select
              value={prodiForm.strata}
              onChange={(e) => setProdiField('strata', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {STRATA_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Nama */}
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Nama <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={prodiForm.nama}
              onChange={(e) => setProdiField('nama', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Nama lengkap program studi"
            />
          </div>

          {/* Singkat */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Singkat <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={prodiForm.singkat}
              onChange={(e) => setProdiField('singkat', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: S1 MTK"
            />
          </div>

          {/* Kategori */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Kategori <span className="text-red-500">*</span>
            </label>
            <select
              value={prodiForm.kategori}
              onChange={(e) => setProdiField('kategori', e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {KATEGORI_OPTIONS.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>

          {/* is_active — only on edit */}
          {editProdi && (
            <div className="col-span-2 flex items-center gap-2">
              <input
                id="prodi_is_active"
                type="checkbox"
                checked={prodiForm.is_active}
                onChange={(e) => setProdiField('is_active', e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
              />
              <label htmlFor="prodi_is_active" className="text-sm text-slate-700">
                Prodi aktif
              </label>
            </div>
          )}
        </div>

        {(createProdiMutation.isError || updateProdiMutation.isError) && (
          <p className="mt-3 text-xs text-red-600">
            Gagal menyimpan data. Periksa kembali isian Anda.
          </p>
        )}
      </FormModal>

      {/* ── Kurikulum Modal ── */}
      <FormModal
        open={kurikulumModalOpen}
        onClose={closeKurikulumModal}
        title={editKurikulum ? 'Edit Kurikulum' : 'Tambah Kurikulum'}
        onSubmit={handleKurikulumSubmit}
        loading={isKurikulumSaving}
        size="sm"
      >
        <div className="flex flex-col gap-4">
          {/* Kode */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Kode <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={kurikulumForm.kode}
              onChange={(e) => setKurikulumField('kode', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: KUR2020"
            />
          </div>

          {/* Tahun */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Tahun <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={kurikulumForm.tahun}
              onChange={(e) => setKurikulumField('tahun', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: 2020"
            />
          </div>

          {/* is_active — only on edit */}
          {editKurikulum && (
            <div className="flex items-center gap-2">
              <input
                id="kurikulum_is_active"
                type="checkbox"
                checked={kurikulumForm.is_active}
                onChange={(e) => setKurikulumField('is_active', e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
              />
              <label htmlFor="kurikulum_is_active" className="text-sm text-slate-700">
                Kurikulum aktif
              </label>
            </div>
          )}
        </div>

        {(createKurikulumMutation.isError || updateKurikulumMutation.isError) && (
          <p className="mt-3 text-xs text-red-600">
            Gagal menyimpan data. Periksa kembali isian Anda.
          </p>
        )}
      </FormModal>
    </div>
  )
}
