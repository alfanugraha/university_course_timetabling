import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Upload, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2 } from 'lucide-react'

import { Badge } from '@/components/Badge'
import { getSesiList, SesiJadwal } from '@/api/sesi'
import { importMaster, importJadwal, ImportResult, ImportWarning } from '@/api/importExport'

// ─── ImportResultPanel ────────────────────────────────────────────────────────

function ImportResultPanel({ result }: { result: ImportResult }) {
  const [showWarnings, setShowWarnings] = useState(false)

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4 space-y-3">
      {/* Summary counts */}
      <div className="flex items-center gap-2">
        <CheckCircle2 size={16} className="text-green-600 shrink-0" />
        <span className="text-sm font-medium text-slate-800">Import selesai</span>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Total" value={result.total} />
        <StatCard label="Ditambah" value={result.inserted} color="green" />
        <StatCard label="Diperbarui" value={result.updated} color="blue" />
        <StatCard label="Dilewati" value={result.skipped} color="amber" />
      </div>

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div>
          <button
            onClick={() => setShowWarnings((v) => !v)}
            className="flex items-center gap-1.5 text-xs font-medium text-amber-700 hover:text-amber-900"
          >
            <AlertTriangle size={13} />
            {result.warnings.length} peringatan
            {showWarnings ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {showWarnings && (
            <div className="mt-2 max-h-64 overflow-y-auto rounded-md border border-amber-200 bg-amber-50">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="border-b border-amber-200 bg-amber-100">
                    <th className="px-3 py-2 text-left font-semibold text-amber-800">Baris</th>
                    <th className="px-3 py-2 text-left font-semibold text-amber-800">Sheet</th>
                    <th className="px-3 py-2 text-left font-semibold text-amber-800">Nilai</th>
                    <th className="px-3 py-2 text-left font-semibold text-amber-800">Alasan</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-amber-100">
                  {result.warnings.map((w: ImportWarning, i: number) => (
                    <tr key={i} className="hover:bg-amber-100">
                      <td className="px-3 py-1.5 text-amber-900">{w.row}</td>
                      <td className="px-3 py-1.5 text-amber-900">{w.sheet}</td>
                      <td className="px-3 py-1.5 text-amber-900 max-w-[160px] truncate" title={w.value}>{w.value}</td>
                      <td className="px-3 py-1.5 text-amber-900">{w.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  color = 'slate',
}: {
  label: string
  value: number
  color?: 'green' | 'blue' | 'amber' | 'slate'
}) {
  const colorMap = {
    green: 'text-green-700 bg-green-50 border-green-200',
    blue: 'text-blue-700 bg-blue-50 border-blue-200',
    amber: 'text-amber-700 bg-amber-50 border-amber-200',
    slate: 'text-slate-700 bg-slate-50 border-slate-200',
  }
  return (
    <div className={`rounded-md border px-3 py-2 text-center ${colorMap[color]}`}>
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[11px] font-medium">{label}</div>
    </div>
  )
}

// ─── ImportSection ────────────────────────────────────────────────────────────

interface ImportSectionProps {
  title: string
  description: string
  onUpload: (file: File) => Promise<ImportResult>
  extra?: React.ReactNode
  disabled?: boolean
}

function ImportSection({ title, description, onUpload, extra, disabled }: ImportSectionProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null
    setFile(f)
    setResult(null)
    setError(null)
  }

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await onUpload(file)
      setResult(res)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Terjadi kesalahan saat upload. Coba lagi.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
      </div>

      {/* Extra controls (e.g. sesi selector) */}
      {extra}

      {/* File input row */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx"
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          {file ? file.name : 'Pilih file .xlsx'}
        </button>

        {file && (
          <Badge variant="info" size="sm">{(file.size / 1024).toFixed(1)} KB</Badge>
        )}

        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || loading || disabled}
          className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Upload size={14} />
          {loading ? 'Mengupload…' : 'Upload'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Result */}
      {result && <ImportResultPanel result={result} />}
    </div>
  )
}

// ─── ImportPage ───────────────────────────────────────────────────────────────

export default function ImportPage() {
  const [selectedSesiId, setSelectedSesiId] = useState('')

  const { data: sesiList = [], isLoading: sesiLoading } = useQuery<SesiJadwal[]>({
    queryKey: ['sesi'],
    queryFn: getSesiList,
  })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-base font-semibold text-slate-900">Import Data</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Upload file Excel untuk data master dan jadwal perkuliahan
        </p>
      </div>

      {/* Section 1: Import Data Master */}
      <ImportSection
        title="Import Data Master"
        description="Upload file db.xlsx untuk mengimpor data prodi, dosen, ruang, kurikulum, dan mata kuliah."
        onUpload={(file) => importMaster(file)}
      />

      {/* Section 2: Import Jadwal */}
      <ImportSection
        title="Import Jadwal"
        description="Upload file Excel jadwal untuk mengimpor assignment ke sesi yang dipilih."
        disabled={!selectedSesiId}
        onUpload={(file) => importJadwal(file, selectedSesiId)}
        extra={
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">
              Sesi Jadwal <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedSesiId}
              onChange={(e) => setSelectedSesiId(e.target.value)}
              disabled={sesiLoading}
              className="w-64 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:opacity-60"
            >
              <option value="">— Pilih sesi —</option>
              {sesiList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nama} ({s.semester} {s.tahun_akademik})
                </option>
              ))}
            </select>
            {!selectedSesiId && (
              <p className="text-[11px] text-slate-400">Pilih sesi terlebih dahulu sebelum upload.</p>
            )}
          </div>
        }
      />
    </div>
  )
}
