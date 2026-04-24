import { Routes, Route, Navigate } from 'react-router-dom'

import Layout from '@/components/Layout'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import ProfilePage from '@/pages/ProfilePage'

import DosenPage from '@/pages/master/DosenPage'
import MataKuliahPage from '@/pages/master/MataKuliahPage'
import RuangPage from '@/pages/master/RuangPage'
import TimeslotPage from '@/pages/master/TimeslotPage'
import ProdiPage from '@/pages/master/ProdiPage'

import SesiListPage from '@/pages/jadwal/SesiListPage'
import SesiDetailPage from '@/pages/jadwal/SesiDetailPage'
import TeamTeachingPage from '@/pages/jadwal/TeamTeachingPage'
import KonflikPage from '@/pages/jadwal/KonflikPage'
import ReviewPage from '@/pages/jadwal/ReviewPage'

import SksRekapPage from '@/pages/laporan/SksRekapPage'
import RoomMapPage from '@/pages/laporan/RoomMapPage'
import PreferensiSummaryPage from '@/pages/laporan/PreferensiSummaryPage'

import JadwalSayaPage from '@/pages/dosen/JadwalSayaPage'
import PreferensiPage from '@/pages/dosen/PreferensiPage'
import PreferensiHariPage from '@/pages/dosen/PreferensiHariPage'
import TeamTeachingDosenPage from '@/pages/dosen/TeamTeachingDosenPage'

import ImportPage from '@/pages/admin/ImportPage'

function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />

      {/* Protected — wrapped in Layout */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Data Master */}
        <Route path="/master/dosen" element={<DosenPage />} />
        <Route path="/master/mata-kuliah" element={<MataKuliahPage />} />
        <Route path="/master/ruang" element={<RuangPage />} />
        <Route path="/master/timeslot" element={<TimeslotPage />} />
        <Route path="/master/prodi" element={<ProdiPage />} />

        {/* Penjadwalan */}
        <Route path="/sesi" element={<SesiListPage />} />
        <Route path="/sesi/:id" element={<SesiDetailPage />} />
        <Route path="/sesi/:id/team-teaching" element={<TeamTeachingPage />} />
        <Route path="/sesi/:id/konflik" element={<KonflikPage />} />
        <Route path="/sesi/:id/review" element={<ReviewPage />} />

        {/* Laporan */}
        <Route path="/laporan/sks" element={<SksRekapPage />} />
        <Route path="/laporan/ruang" element={<RoomMapPage />} />
        <Route path="/laporan/preferensi" element={<PreferensiSummaryPage />} />

        {/* Dosen */}
        <Route path="/jadwal-saya" element={<JadwalSayaPage />} />
        <Route path="/preferensi" element={<PreferensiPage />} />
        <Route path="/preferensi/hari" element={<PreferensiHariPage />} />
        <Route path="/team-teaching" element={<TeamTeachingDosenPage />} />

        {/* Admin */}
        <Route path="/import" element={<ImportPage />} />

        {/* Profil */}
        <Route path="/profile" element={<ProfilePage />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}

export default App
