import { Routes, Route } from 'react-router-dom'
import { motion } from 'framer-motion'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewReview from './pages/NewReview'
import ReviewDetail from './pages/ReviewDetail'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewReview />} />
        <Route path="/review/:id" element={<ReviewDetail />} />
      </Routes>
    </Layout>
  )
}

export default App

