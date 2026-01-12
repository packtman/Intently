import { Routes, Route } from 'react-router-dom'
import { motion } from 'framer-motion'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewReview from './pages/NewReview'
import Reviews from './pages/Reviews'
import ReviewDetail from './pages/ReviewDetail'
import TeamQueue from './pages/TeamQueue'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewReview />} />
        <Route path="/reviews" element={<Reviews />} />
        <Route path="/review/:id" element={<ReviewDetail />} />
        <Route path="/teams/:team/queue" element={<TeamQueue />} />
      </Routes>
    </Layout>
  )
}

export default App

