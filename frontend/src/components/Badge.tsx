import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

type BadgeVariant =
  // Sesi status
  | 'Draft'
  | 'Aktif'
  | 'Arsip'
  // Conflict severity
  | 'ERROR'
  | 'WARNING'
  // General
  | 'success'
  | 'info'
  | 'default'
  | string // allow arbitrary strings, falls back to default

type BadgeSize = 'sm' | 'md'

interface BadgeProps {
  variant?: BadgeVariant
  size?: BadgeSize
  children: React.ReactNode
  className?: string
}

// ─── Variant map ──────────────────────────────────────────────────────────────

const VARIANT_CLASSES: Record<string, string> = {
  // Sesi status
  Draft: 'bg-slate-100 text-slate-600',
  Aktif: 'bg-green-100 text-green-700',
  Arsip: 'bg-slate-200 text-slate-500',
  // Conflict severity
  ERROR: 'bg-red-100 text-red-700',
  WARNING: 'bg-amber-100 text-amber-700',
  // General
  success: 'bg-green-100 text-green-700',
  info: 'bg-blue-100 text-blue-700',
  default: 'bg-slate-100 text-slate-600',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Badge({ variant = 'default', size = 'md', children, className }: BadgeProps) {
  const colorClass = VARIANT_CLASSES[variant] ?? VARIANT_CLASSES.default

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
        colorClass,
        className
      )}
    >
      {children}
    </span>
  )
}
