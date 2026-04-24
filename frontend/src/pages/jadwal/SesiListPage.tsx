import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, Eye } from 'lucide-react'

import { DataTable, ColumnDef } from '@/components/DataTable'
import { FormModal } from '@/components/FormModal'
import { Badge } from '@/components/Badge'
import { useAuthStore } from '@/store/authStore'

import {
  getSesiList,
  createSesi,
  SesiJadwal,
  SesiCreatePayload,
  SesiSemester,
} from '@/api/sesi'

// ─── Constants ────────────────────────────────────────────────────────────────

const EDITOR_ROLES_JURUSAN = ['admin', 'sekretaris_jurusan', 'tendik_jurusan']

const SEMESTER_OPTIONS: SesiSemester[] = ['Ganjil', 'Genap']

const EMPTY_FORM: SesiCreatePayload = {
  nama: '',
  semester: 'Ganjil',
  tahun_akademik: '',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function SesiListPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const canEdit = user ? EDITOR_ROLES_JURUSAN.includes(user.role) : false

  // ── Modal state ───────────────────────────────────────────────────────────
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState<SesiCreatePayload>(EMPTY_FORM)

  // ── Query ─────────────────────────────────────────────────────────────────
  const { data: sesiList = [], isLoading, isError } = useQuery({
    queryKey: ['sesi'],
    queryFn: getSesiList,
  })

  // ── Mutation ──────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: createSesi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sesi'] })
      closeModal()
    },
  })

  // ── Handlers ──────────────────────────────────────────────────────────────
  function openAdd() {
    setForm(EMPTY_FORM)
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setForm(EMPTY_FORM)
  }

  function handleSubmit() {
    createMutation.mutate(form)
  }

  function setField<K extends keyof SesiCreatePayload>(key: K, value: SesiCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Columns ───────────────────────────────────────────────────────────────
  const columns: ColumnDef<Record<string, unknown>>[] = [
    { key: 'nama', label: 'Nama', sortable: true },
    { key: 'semester', label: 'Semester', sortable: true },
    { key: 'tahun_akademik', label: 'Tahun Akademik', sortable: true },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (val) => {
        const status = val as SesiJadwal['status']
        return <Badge variant={status}>{status}</Badge>
      },
    },
    {
      key: 'created_at',
      label: 'Dibuat',
      sortable: true,
      render: (val) => formatDate(val as string),
    },
    {
      key: 'actions',
      label: '',
      render: (_: unknown, row: Record<string, unknown>) => (
        <button
          onClick={() => navigate(`/sesi/${row.id}`)}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800"
        >
          <Eye size={13} />
          Lihat Detail
        </button>
      ),
    },
  ]

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-slate-900">Daftar Sesi Jadwal</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manajemen sesi penjadwalan per semester</p>
        </div>
        {canEdit && (
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            <Plus size={15} />
            Buat Sesi Baru
          </button>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Gagal memuat data sesi. Silakan coba lagi.
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={sesiList as unknown as Record<string, unknown>[]}
        loading={isLoading}
        emptyMessage="Belum ada sesi jadwal."
      />

      {/* Create Modal */}
      <FormModal
        open={modalOpen}
        onClose={closeModal}
        title="Buat Sesi Baru"
        onSubmit={handleSubmit}
        loading={createMutation.isPending}
        submitLabel="Buat Sesi"
      >
        <div className="flex flex-col gap-4">
          {/* Nama */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Nama Sesi <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.nama}
              onChange={(e) => setField('nama', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: Jadwal Ganjil 2025-2026"
            />
          </div>

          {/* Semester */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Semester <span className="text-red-500">*</span>
            </label>
            <select
              value={form.semester}
              onChange={(e) => setField('semester', e.target.value as SesiSemester)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              {SEMESTER_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Tahun Akademik */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Tahun Akademik <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.tahun_akademik}
              onChange={(e) => setField('tahun_akademik', e.target.value)}
              required
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400"
              placeholder="Contoh: 2025-2026"
            />
          </div>
        </div>

        {/* Mutation error */}
        {createMutation.isError && (
          <p className="mt-3 text-xs text-red-600">
            Gagal membuat sesi. Periksa kembali isian Anda.
          </p>
        )}
      </FormModal>
    </div>
  )
}
