import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// Dev  : VITE_API_URL is not set → baseURL '/api' → handled by Vite proxy or nginx
// Prod : VITE_API_URL = 'https://<api-service>.up.railway.app' → direct API URL
const baseURL = import.meta.env.VITE_API_URL ?? '/api'

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Render free tier spins down after 15 min idle; first request after cold
  // start can take ~30 s. Cap at 40 s so the UI shows an error instead of
  // hanging indefinitely.
  timeout: 40_000,
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Skip the global 401 handler for the login endpoint itself so that
    // Login.tsx can catch it and show "username/password salah" to the user.
    const isAuthEndpoint = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
