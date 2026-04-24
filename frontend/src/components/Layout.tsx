import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Users,
  BookOpen,
  DoorOpen,
  Clock,
  GraduationCap,
  CalendarDays,
  BarChart3,
  Map,
  Star,
  Upload,
  LogOut,
  ChevronRight,
  CalendarCheck,
  UserCircle,
  UsersRound,
} from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────────────────────

type Role =
  | 'admin'
  | 'ketua_jurusan'
  | 'sekretaris_jurusan'
  | 'koordinator_prodi'
  | 'tendik_jurusan'
  | 'tendik_prodi'
  | 'dosen'

interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
  roles?: Role[] // undefined = all roles
}

interface NavSection {
  title: string
  items: NavItem[]
  roles?: Role[] // section-level visibility
}

// ─── Navigation Config ────────────────────────────────────────────────────────

const NAV_SECTIONS: NavSection[] = [
  {
    title: '',
    items: [
      {
        label: 'Dashboard',
        to: '/dashboard',
        icon: <LayoutDashboard size={16} />,
      },
    ],
  },
  {
    title: 'Data Master',
    roles: ['admin', 'sekretaris_jurusan', 'tendik_jurusan', 'koordinator_prodi', 'tendik_prodi'],
    items: [
      { label: 'Dosen', to: '/master/dosen', icon: <Users size={16} /> },
      { label: 'Mata Kuliah', to: '/master/mata-kuliah', icon: <BookOpen size={16} /> },
      { label: 'Ruang', to: '/master/ruang', icon: <DoorOpen size={16} /> },
      { label: 'Timeslot', to: '/master/timeslot', icon: <Clock size={16} /> },
      { label: 'Prodi & Kurikulum', to: '/master/prodi', icon: <GraduationCap size={16} /> },
    ],
  },
  {
    title: 'Penjadwalan',
    roles: ['admin', 'ketua_jurusan', 'sekretaris_jurusan', 'koordinator_prodi', 'tendik_jurusan', 'tendik_prodi'],
    items: [
      { label: 'Daftar Sesi', to: '/sesi', icon: <CalendarDays size={16} /> },
    ],
  },
  {
    title: 'Jadwal Saya',
    roles: ['dosen'],
    items: [
      { label: 'Jadwal Saya', to: '/jadwal-saya', icon: <CalendarCheck size={16} /> },
      { label: 'Unavailability', to: '/preferensi', icon: <Star size={16} /> },
      { label: 'Preferensi Hari', to: '/preferensi/hari', icon: <CalendarDays size={16} /> },
      { label: 'Team Teaching', to: '/team-teaching', icon: <UsersRound size={16} /> },
    ],
  },
  {
    title: 'Laporan',
    roles: ['admin', 'ketua_jurusan', 'sekretaris_jurusan', 'koordinator_prodi', 'tendik_jurusan', 'tendik_prodi'],
    items: [
      { label: 'Rekap SKS', to: '/laporan/sks', icon: <BarChart3 size={16} /> },
      { label: 'Peta Ruang', to: '/laporan/ruang', icon: <Map size={16} /> },
      { label: 'Preferensi', to: '/laporan/preferensi', icon: <Star size={16} /> },
    ],
  },
  {
    title: 'Admin',
    roles: ['admin'],
    items: [
      { label: 'Import', to: '/import', icon: <Upload size={16} /> },
    ],
  },
]

// ─── Breadcrumb helpers ───────────────────────────────────────────────────────

const SEGMENT_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  master: 'Data Master',
  dosen: 'Dosen',
  'mata-kuliah': 'Mata Kuliah',
  ruang: 'Ruang',
  timeslot: 'Timeslot',
  prodi: 'Prodi & Kurikulum',
  sesi: 'Daftar Sesi',
  laporan: 'Laporan',
  sks: 'Rekap SKS',
  preferensi: 'Preferensi',
  hari: 'Preferensi Hari',
  import: 'Import',
  'jadwal-saya': 'Jadwal Saya',
  'team-teaching': 'Team Teaching',
  konflik: 'Konflik',
  review: 'Review',
  profile: 'Profil Saya',
}

function isUUID(segment: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(segment)
}

interface BreadcrumbSegment {
  label: string
  path: string
}

function buildBreadcrumbs(pathname: string): BreadcrumbSegment[] {
  const segments = pathname.split('/').filter(Boolean)
  const crumbs: BreadcrumbSegment[] = []
  let accumulated = ''

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i]
    accumulated += `/${seg}`

    if (isUUID(seg)) {
      // Replace UUID with context-aware label
      const parent = segments[i - 1]
      if (parent === 'sesi') {
        crumbs.push({ label: 'Detail Sesi', path: accumulated })
      } else {
        crumbs.push({ label: 'Detail', path: accumulated })
      }
    } else {
      const label = SEGMENT_LABELS[seg] ?? seg
      crumbs.push({ label, path: accumulated })
    }
  }

  return crumbs
}

// ─── Role badge color ─────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  ketua_jurusan: 'Ketua Jurusan',
  sekretaris_jurusan: 'Sekretaris',
  koordinator_prodi: 'Koordinator Prodi',
  tendik_jurusan: 'Tendik Jurusan',
  tendik_prodi: 'Tendik Prodi',
  dosen: 'Dosen',
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  ketua_jurusan: 'bg-purple-100 text-purple-700',
  sekretaris_jurusan: 'bg-blue-100 text-blue-700',
  koordinator_prodi: 'bg-green-100 text-green-700',
  tendik_jurusan: 'bg-orange-100 text-orange-700',
  tendik_prodi: 'bg-yellow-100 text-yellow-700',
  dosen: 'bg-slate-100 text-slate-700',
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Layout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  const role = (user?.role ?? '') as Role

  const visibleSections = NAV_SECTIONS.filter((section) => {
    if (!section.roles) return true
    return section.roles.includes(role)
  })

  const breadcrumbs = buildBreadcrumbs(location.pathname)

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-60 flex-shrink-0 flex flex-col bg-white border-r border-slate-200 overflow-y-auto">
        {/* Logo / App name */}
        <div className="px-4 py-4 border-b border-slate-100">
          <span className="text-sm font-semibold text-slate-800 leading-tight">
            Sistem Penjadwalan
          </span>
          <p className="text-xs text-slate-400 mt-0.5">Jurusan Matematika UNRI</p>
        </div>

        {/* Nav sections */}
        <nav className="flex-1 px-2 py-3 space-y-4">
          {visibleSections.map((section) => (
            <div key={section.title || '__root'}>
              {section.title && (
                <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {section.title}
                </p>
              )}
              <ul className="space-y-0.5">
                {section.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/dashboard'}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-sm transition-colors',
                          isActive
                            ? 'bg-slate-100 text-slate-900 font-medium'
                            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                        )
                      }
                    >
                      <span className="text-slate-400">{item.icon}</span>
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* User info + logout */}
        <div className="border-t border-slate-100 px-3 py-3">
          {user && (
            <div className="mb-2">
              <p className="text-sm font-medium text-slate-800 truncate">{user.username}</p>
              <span
                className={cn(
                  'inline-block mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium',
                  ROLE_COLORS[user.role] ?? 'bg-slate-100 text-slate-600'
                )}
              >
                {ROLE_LABELS[user.role] ?? user.role}
              </span>
            </div>
          )}
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-sm transition-colors mb-0.5',
                isActive
                  ? 'bg-slate-100 text-slate-900 font-medium'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
              )
            }
          >
            <UserCircle size={15} />
            Profil
          </NavLink>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-sm text-slate-500 hover:bg-slate-50 hover:text-red-600 transition-colors"
          >
            <LogOut size={15} />
            Keluar
          </button>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-3">
          {/* Breadcrumb */}
          <nav aria-label="breadcrumb">
            <ol className="flex items-center gap-1 text-sm text-slate-500">
              {breadcrumbs.map((crumb, idx) => {
                const isLast = idx === breadcrumbs.length - 1
                return (
                  <li key={crumb.path} className="flex items-center gap-1">
                    {idx > 0 && <ChevronRight size={13} className="text-slate-300" />}
                    {isLast ? (
                      <span className="font-medium text-slate-800">{crumb.label}</span>
                    ) : (
                      <NavLink
                        to={crumb.path}
                        className="hover:text-slate-800 transition-colors"
                      >
                        {crumb.label}
                      </NavLink>
                    )}
                  </li>
                )
              })}
            </ol>
          </nav>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
