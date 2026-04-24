import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { LogOut, User, Mail, Shield, BookOpen } from 'lucide-react'

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin Sistem',
  ketua_jurusan: 'Ketua Jurusan',
  sekretaris_jurusan: 'Sekretaris Jurusan',
  koordinator_prodi: 'Koordinator Prodi',
  dosen: 'Dosen',
  tendik_prodi: 'Tendik Prodi',
  tendik_jurusan: 'Tendik Jurusan',
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

export default function ProfilePage() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  if (!user) return null

  const roleLabel = ROLE_LABELS[user.role] ?? user.role
  const roleColor = ROLE_COLORS[user.role] ?? 'bg-slate-100 text-slate-600'

  return (
    <div className="max-w-lg">
      <h1 className="text-xl font-semibold text-slate-800 mb-6">Profil Saya</h1>

      <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
        {/* Avatar + name */}
        <div className="px-6 py-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0">
            <User size={22} className="text-slate-500" />
          </div>
          <div>
            <p className="text-base font-semibold text-slate-800">{user.username}</p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${roleColor}`}>
              {roleLabel}
            </span>
          </div>
        </div>

        {/* Info rows */}
        <div className="px-6 py-4 flex items-center gap-3">
          <Mail size={16} className="text-slate-400 flex-shrink-0" />
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Email</p>
            <p className="text-sm text-slate-700">{user.email ?? '—'}</p>
          </div>
        </div>

        <div className="px-6 py-4 flex items-center gap-3">
          <Shield size={16} className="text-slate-400 flex-shrink-0" />
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Role</p>
            <p className="text-sm text-slate-700">{roleLabel}</p>
          </div>
        </div>

        {user.prodi_id && (
          <div className="px-6 py-4 flex items-center gap-3">
            <BookOpen size={16} className="text-slate-400 flex-shrink-0" />
            <div>
              <p className="text-xs text-slate-400 mb-0.5">Prodi</p>
              <p className="text-sm text-slate-700">{user.prodi_id}</p>
            </div>
          </div>
        )}
      </div>

      {/* Logout */}
      <div className="mt-6">
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors"
        >
          <LogOut size={15} />
          Keluar dari Sistem
        </button>
      </div>
    </div>
  )
}
