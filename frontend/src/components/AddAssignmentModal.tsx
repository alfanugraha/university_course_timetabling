import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { FormModal } from '@/components/FormModal'
import { getProdi } from '@/api/prodi'
import { getKurikulum } from '@/api/kurikulum'
import { getMataKuliah, getKelas } from '@/api/mataKuliah'
import { getDosen } from '@/api/dosen'
import { getTimeslots } from '@/api/timeslot'
import { getRuang } from '@/api/ruang'
import { createAssignment, AssignmentCreatePayload } from '@/api/assignment'

// ─── Types ────────────────────────────────────────────────────────────────────

interface KelasOption {
  id: string
  label: string
}

interface AddAssignmentModalProps {
  open: boolean
  onClose: () => void
  sesiId: string
  onSuccess: () => void
}

// ─── Style helpers ────────────────────────────────────────────────────────────

const selectCls =
  'w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:bg-slate-50 disabled:text-slate-400'
const labelCls = 'block text-xs font-medium text-slate-600 mb-1'

// ─── Component ────────────────────────────────────────────────────────────────

export function AddAssignmentModal({
  open,
  onClose,
  sesiId,
  onSuccess,
}: AddAssignmentModalProps) {
  const queryClient = useQueryClient()

  // ── Cascade state ─────────────────────────────────────────────────────────
  const [prodiId, setProdiId] = useState('')
  const [kurikulumId, setKurikulumId] = useState('')
  const [semester, setSemester] = useState('')
  const [mkKelasId, setMkKelasId] = useState('')
  const [dosen1Id, setDosen1Id] = useState('')
  const [dosen2Id, setDosen2Id] = useState('')
  const [timeslotId, setTimeslotId] = useState('')
  const [ruangId, setRuangId] = useState('')
  const [catatan, setCatatan] = useState('')
  const [submitError, setSubmitError] = useState<string | null>(null)

  // ── Queries ───────────────────────────────────────────────────────────────

  const { data: prodiList = [] } = useQuery({
    queryKey: ['prodi'],
    queryFn: getProdi,
    enabled: open,
  })

  const { data: kurikulumAll = [] } = useQuery({
    queryKey: ['kurikulum'],
    queryFn: getKurikulum,
    enabled: open,
  })

  const { data: dosenList = [], isLoading: dosenLoading } = useQuery({
    queryKey: ['dosen', 'Aktif'],
    queryFn: () => getDosen({ status: 'Aktif' }),
    enabled: open,
  })

  const { data: timeslotList = [], isLoading: timeslotLoading } = useQuery({
    queryKey: ['timeslots'],
    queryFn: getTimeslots,
    enabled: open,
  })

  const { data: ruangList = [], isLoading: ruangLoading } = useQuery({
    queryKey: ['ruang'],
    queryFn: getRuang,
    enabled: open,
  })

  // Kelas MK: fetch MK list then kelas for each MK
  const { data: kelasOptions = [], isLoading: kelasLoading } = useQuery({
    queryKey: ['mk-kelas-options', kurikulumId, semester],
    queryFn: async (): Promise<KelasOption[]> => {
      const mkList = await getMataKuliah({
        kurikulum_id: kurikulumId,
        semester: Number(semester),
      })
      if (mkList.length === 0) return []
      const kelasByMk = await Promise.all(mkList.map((mk) => getKelas(mk.id)))
      return kelasByMk.flat().map((k) => ({ id: k.id, label: k.label }))
    },
    enabled: !!kurikulumId && !!semester,
  })

  // ── Derived ───────────────────────────────────────────────────────────────

  const kurikulumFiltered = kurikulumAll.filter((k) => k.prodi_id === prodiId)

  // ── Cascade reset helpers ─────────────────────────────────────────────────

  function handleProdiChange(val: string) {
    setProdiId(val)
    setKurikulumId('')
    setSemester('')
    setMkKelasId('')
    setDosen1Id('')
    setDosen2Id('')
    setTimeslotId('')
    setRuangId('')
  }

  function handleKurikulumChange(val: string) {
    setKurikulumId(val)
    setSemester('')
    setMkKelasId('')
    setDosen1Id('')
    setDosen2Id('')
    setTimeslotId('')
    setRuangId('')
  }

  function handleSemesterChange(val: string) {
    setSemester(val)
    setMkKelasId('')
    setDosen1Id('')
    setDosen2Id('')
    setTimeslotId('')
    setRuangId('')
  }

  function handleMkKelasChange(val: string) {
    setMkKelasId(val)
    setDosen1Id('')
    setDosen2Id('')
    setTimeslotId('')
    setRuangId('')
  }

  function handleDosen1Change(val: string) {
    setDosen1Id(val)
    setDosen2Id('')
  }

  function handleTimeslotChange(val: string) {
    setTimeslotId(val)
    setRuangId('')
  }

  // ── Mutation ──────────────────────────────────────────────────────────────

  const mutation = useMutation({
    mutationFn: (payload: AssignmentCreatePayload) =>
      createAssignment(sesiId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments', sesiId] })
      onSuccess()
      onClose()
    },
    onError: (err: Error) => {
      setSubmitError(err.message || 'Gagal menyimpan assignment.')
    },
  })

  function handleSubmit() {
    setSubmitError(null)
    if (!mkKelasId || !dosen1Id || !timeslotId) {
      setSubmitError('Kelas MK, Dosen I, dan Timeslot wajib diisi.')
      return
    }
    mutation.mutate({
      mk_kelas_id: mkKelasId,
      dosen1_id: dosen1Id,
      dosen2_id: dosen2Id || null,
      timeslot_id: timeslotId,
      ruang_id: ruangId || null,
      catatan: catatan || null,
    })
  }

  function handleClose() {
    // reset all state on close
    setProdiId('')
    setKurikulumId('')
    setSemester('')
    setMkKelasId('')
    setDosen1Id('')
    setDosen2Id('')
    setTimeslotId('')
    setRuangId('')
    setCatatan('')
    setSubmitError(null)
    onClose()
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <FormModal
      open={open}
      onClose={handleClose}
      title="Tambah Assignment"
      onSubmit={handleSubmit}
      submitLabel="Simpan"
      loading={mutation.isPending}
      size="lg"
    >
      <div className="space-y-4">
        {/* Error */}
        {submitError && (
          <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {submitError}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {/* 1. Prodi */}
          <div>
            <label className={labelCls}>Prodi</label>
            <select
              value={prodiId}
              onChange={(e) => handleProdiChange(e.target.value)}
              className={selectCls}
            >
              <option value="">— Pilih Prodi —</option>
              {prodiList
                .filter((p) => p.is_active)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.singkat} — {p.nama}
                  </option>
                ))}
            </select>
          </div>

          {/* 2. Kurikulum */}
          <div>
            <label className={labelCls}>Kurikulum</label>
            <select
              value={kurikulumId}
              onChange={(e) => handleKurikulumChange(e.target.value)}
              disabled={!prodiId}
              className={selectCls}
            >
              <option value="">— Pilih Kurikulum —</option>
              {kurikulumFiltered.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.kode} ({k.tahun})
                </option>
              ))}
            </select>
          </div>

          {/* 3. Semester */}
          <div>
            <label className={labelCls}>Semester</label>
            <select
              value={semester}
              onChange={(e) => handleSemesterChange(e.target.value)}
              disabled={!kurikulumId}
              className={selectCls}
            >
              <option value="">— Pilih Semester —</option>
              {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                <option key={s} value={String(s)}>
                  Semester {s}
                </option>
              ))}
            </select>
          </div>

          {/* 4. Kelas MK */}
          <div>
            <label className={labelCls}>Kelas MK</label>
            <select
              value={mkKelasId}
              onChange={(e) => handleMkKelasChange(e.target.value)}
              disabled={!semester || kelasLoading}
              className={selectCls}
            >
              <option value="">
                {kelasLoading ? 'Memuat...' : '— Pilih Kelas MK —'}
              </option>
              {kelasOptions.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>

          {/* 5. Dosen I */}
          <div>
            <label className={labelCls}>Dosen I <span className="text-red-500">*</span></label>
            <select
              value={dosen1Id}
              onChange={(e) => handleDosen1Change(e.target.value)}
              disabled={!mkKelasId || dosenLoading}
              className={selectCls}
            >
              <option value="">
                {dosenLoading ? 'Memuat...' : '— Pilih Dosen I —'}
              </option>
              {dosenList.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.kode} — {d.nama}
                </option>
              ))}
            </select>
          </div>

          {/* 6. Dosen II */}
          <div>
            <label className={labelCls}>Dosen II <span className="text-slate-400 font-normal">(opsional)</span></label>
            <select
              value={dosen2Id}
              onChange={(e) => setDosen2Id(e.target.value)}
              disabled={!dosen1Id || dosenLoading}
              className={selectCls}
            >
              <option value="">— Pilih Dosen II —</option>
              {dosenList
                .filter((d) => d.id !== dosen1Id)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.kode} — {d.nama}
                  </option>
                ))}
            </select>
          </div>

          {/* 7. Timeslot */}
          <div>
            <label className={labelCls}>Timeslot <span className="text-red-500">*</span></label>
            <select
              value={timeslotId}
              onChange={(e) => handleTimeslotChange(e.target.value)}
              disabled={!mkKelasId || timeslotLoading}
              className={selectCls}
            >
              <option value="">
                {timeslotLoading ? 'Memuat...' : '— Pilih Timeslot —'}
              </option>
              {timeslotList.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.hari} {t.jam_mulai.slice(0, 5)}–{t.jam_selesai.slice(0, 5)}
                </option>
              ))}
            </select>
          </div>

          {/* 8. Ruang */}
          <div>
            <label className={labelCls}>Ruang <span className="text-slate-400 font-normal">(opsional)</span></label>
            <select
              value={ruangId}
              onChange={(e) => setRuangId(e.target.value)}
              disabled={!timeslotId || ruangLoading}
              className={selectCls}
            >
              <option value="">
                {ruangLoading ? 'Memuat...' : '— Pilih Ruang —'}
              </option>
              {ruangList
                .filter((r) => r.is_active)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nama}
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Catatan */}
        <div>
          <label className={labelCls}>Catatan <span className="text-slate-400 font-normal">(opsional)</span></label>
          <textarea
            value={catatan}
            onChange={(e) => setCatatan(e.target.value)}
            rows={2}
            placeholder="Catatan tambahan..."
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
          />
        </div>
      </div>
    </FormModal>
  )
}
