import { Routes, Route } from 'react-router-dom'
import { motion } from 'framer-motion'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewReview from './pages/NewReview'
import Reviews from './pages/Reviews'
import ReviewDetail from './pages/ReviewDetail'
import TeamQueue from './pages/TeamQueue'
import BulkAnalysis from './pages/BulkAnalysis'
import PRDGenerator from './pages/PRDGenerator'
import Analytics from './pages/Analytics'
import Chat from './pages/Chat'
import Settings from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewReview />} />
        <Route path="/reviews" element={<Reviews />} />
        <Route path="/review/:id" element={<ReviewDetail />} />
        <Route path="/teams/:team/queue" element={<TeamQueue />} />
        <Route path="/bulk-analysis" element={<BulkAnalysis />} />
        <Route path="/prd-generator" element={<PRDGenerator />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App

