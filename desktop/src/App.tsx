import { Routes, Route, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewReview from './pages/NewReview'
import ReviewDetail from './pages/ReviewDetail'
import Reviews from './pages/Reviews'
import Settings from './pages/Settings'
import BulkAnalysis from './pages/BulkAnalysis'
import PRDGenerator from './pages/PRDGenerator'
import { BackendProvider } from './hooks/useBackend'

function App() {
  const navigate = useNavigate()
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // Listen for menu events from Electron
    const cleanupNewReview = window.electronAPI?.onNewReview?.(() => {
      navigate('/new')
    })

    const cleanupSettings = window.electronAPI?.onOpenSettings?.(() => {
      navigate('/settings')
    })

    setIsReady(true)

    return () => {
      cleanupNewReview?.()
      cleanupSettings?.()
    }
  }, [navigate])

  if (!isReady) {
    return (
      <div className="h-screen w-screen bg-void-950 flex items-center justify-center">
        <div className="animate-pulse text-neon-400">Loading...</div>
      </div>
    )
  }

  return (
    <BackendProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<NewReview />} />
          <Route path="/bulk" element={<BulkAnalysis />} />
          <Route path="/generate" element={<PRDGenerator />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/review/:id" element={<ReviewDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BackendProvider>
  )
}

export default App

