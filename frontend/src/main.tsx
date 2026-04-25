import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, MutationCache } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  // ── Global mutation error logging ────────────────────────────────────────
  // Every useMutation in the app gets this as a fallback. Individual onError
  // handlers in each page still take precedence.
  mutationCache: new MutationCache({
    onError: (error) => {
      console.error('[mutation error]', error)
    },
  }),
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000,       // cache fresh for 5 min
      // Disable refetch-on-focus: Radix Dialog open/close triggers a window
      // focus event that would re-fetch every time a modal appears, causing
      // the table to flicker into a loading skeleton.
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
