import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ColumnDef<T> {
  key: keyof T | string
  label: string
  sortable?: boolean
  render?: (value: unknown, row: T) => React.ReactNode
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: ColumnDef<T>[]
  data: T[]
  pageSize?: number
  loading?: boolean
  emptyMessage?: string
  rowClassName?: (row: T) => string
}

type SortDir = 'asc' | 'desc'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

function getValue<T extends Record<string, unknown>>(row: T, key: string): unknown {
  // Support dot-notation keys like "dosen.nama"
  return key.split('.').reduce<unknown>((acc, k) => {
    if (acc && typeof acc === 'object') return (acc as Record<string, unknown>)[k]
    return undefined
  }, row)
}

function compareValues(a: unknown, b: unknown): number {
  if (a === b) return 0
  if (a == null) return 1
  if (b == null) return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

// ─── Skeleton row ─────────────────────────────────────────────────────────────

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
        </td>
      ))}
    </tr>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  pageSize: initialPageSize = 20,
  loading = false,
  emptyMessage = 'Tidak ada data.',
  rowClassName,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)

  // ── Sort ──────────────────────────────────────────────────────────────────

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
    setPage(1)
  }

  const sorted = useMemo(() => {
    if (!sortKey) return data
    return [...data].sort((a, b) => {
      const va = getValue(a, sortKey)
      const vb = getValue(b, sortKey)
      const cmp = compareValues(va, vb)
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  // ── Pagination ────────────────────────────────────────────────────────────

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const safePage = Math.min(page, totalPages)

  const pageData = useMemo(() => {
    const start = (safePage - 1) * pageSize
    return sorted.slice(start, start + pageSize)
  }, [sorted, safePage, pageSize])

  function handlePageSizeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setPageSize(Number(e.target.value))
    setPage(1)
  }

  // Page number buttons: show up to 5 around current
  const pageNumbers = useMemo(() => {
    const delta = 2
    const range: number[] = []
    for (
      let i = Math.max(1, safePage - delta);
      i <= Math.min(totalPages, safePage + delta);
      i++
    ) {
      range.push(i)
    }
    return range
  }, [safePage, totalPages])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-3">
      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              {columns.map((col) => {
                const key = String(col.key)
                const isActive = sortKey === key
                return (
                  <th
                    key={key}
                    className={cn(
                      'px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500',
                      col.sortable && 'cursor-pointer select-none hover:text-slate-800'
                    )}
                    onClick={col.sortable ? () => handleSort(key) : undefined}
                  >
                    <span className="flex items-center gap-1">
                      {col.label}
                      {col.sortable && (
                        <span className="text-slate-400">
                          {isActive ? (
                            sortDir === 'asc' ? (
                              <ChevronUp size={13} />
                            ) : (
                              <ChevronDown size={13} />
                            )
                          ) : (
                            <ChevronsUpDown size={13} />
                          )}
                        </span>
                      )}
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <SkeletonRow key={i} cols={columns.length} />
              ))
            ) : pageData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center text-sm text-slate-400"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              pageData.map((row, rowIdx) => (
                <tr key={rowIdx} className={cn('hover:bg-slate-50', rowClassName?.(row))}>
                  {columns.map((col) => {
                    const key = String(col.key)
                    const raw = getValue(row, key)
                    return (
                      <td key={key} className="px-4 py-2.5 text-slate-700">
                        {col.render ? col.render(raw, row) : (raw as React.ReactNode) ?? '—'}
                      </td>
                    )
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination bar */}
      {!loading && sorted.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
          {/* Left: items info + page size */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">
              {(safePage - 1) * pageSize + 1}–
              {Math.min(safePage * pageSize, sorted.length)} dari {sorted.length} data
            </span>
            <label className="flex items-center gap-1.5 text-xs text-slate-500">
              Tampilkan
              <select
                value={pageSize}
                onChange={handlePageSizeChange}
                className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400"
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              per halaman
            </label>
          </div>

          {/* Right: page buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage === 1}
              className="rounded p-1 hover:bg-slate-100 disabled:opacity-40"
              aria-label="Halaman sebelumnya"
            >
              <ChevronLeft size={15} />
            </button>

            {pageNumbers[0] > 1 && (
              <>
                <PageBtn n={1} current={safePage} onClick={setPage} />
                {pageNumbers[0] > 2 && (
                  <span className="px-1 text-slate-400">…</span>
                )}
              </>
            )}

            {pageNumbers.map((n) => (
              <PageBtn key={n} n={n} current={safePage} onClick={setPage} />
            ))}

            {pageNumbers[pageNumbers.length - 1] < totalPages && (
              <>
                {pageNumbers[pageNumbers.length - 1] < totalPages - 1 && (
                  <span className="px-1 text-slate-400">…</span>
                )}
                <PageBtn n={totalPages} current={safePage} onClick={setPage} />
              </>
            )}

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage === totalPages}
              className="rounded p-1 hover:bg-slate-100 disabled:opacity-40"
              aria-label="Halaman berikutnya"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── PageBtn helper ───────────────────────────────────────────────────────────

function PageBtn({
  n,
  current,
  onClick,
}: {
  n: number
  current: number
  onClick: (n: number) => void
}) {
  return (
    <button
      onClick={() => onClick(n)}
      className={cn(
        'min-w-[28px] rounded px-1.5 py-0.5 text-xs font-medium',
        n === current
          ? 'bg-slate-900 text-white'
          : 'text-slate-600 hover:bg-slate-100'
      )}
    >
      {n}
    </button>
  )
}
