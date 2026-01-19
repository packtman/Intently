import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HashRouter } from 'react-router-dom'
import App from './App'
import { api } from './services/api'
import './index.css'

// PERFORMANCE OPTIMIZATION: Configure React Query to reduce unnecessary refetches
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      // Cache data for 5 minutes before considering it stale
      staleTime: 5 * 60 * 1000,
      // Keep unused data in cache for 30 minutes
      gcTime: 30 * 60 * 1000,
      // Don't refetch on mount if data exists
      refetchOnMount: false,
      // Don't refetch on reconnect
      refetchOnReconnect: false,
    },
  },
})

// Initialize API service (caches base URL to avoid repeated IPC calls)
api.init()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <App />
      </HashRouter>
    </QueryClientProvider>
  </React.StrictMode>
)

