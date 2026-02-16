import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Shield,
  ArrowRight,
  ArrowLeft,
  Clock,
  Search,
  Filter,
} from 'lucide-react'
import { useState } from 'react'
import { api } from '../services/api'
import { useBackend } from '../hooks/useBackend'
import type { Review } from '../types'

export default function Reviews() {
  const { isConnected } = useBackend()
  const [searchTerm, setSearchTerm] = useState('')
  const [riskFilter, setRiskFilter] = useState<string>('ALL')

  const { data: reviews = [], isLoading } = useQuery<Review[]>({
    queryKey: ['reviews'],
    queryFn: () => api.listReviews(),
    enabled: isConnected,
    // Refetch on mount when data is stale so new reviews show up
    refetchOnMount: true,
    staleTime: 30 * 1000,
  })

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch = review.title.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesRisk = riskFilter === 'ALL' || review.risk_rating === riskFilter
    return matchesSearch && matchesRisk
  })

  if (!isConnected) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-void-400">Backend not connected</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="w-10 h-10 rounded-xl bg-void-800/50 border border-void-700/50 
                       flex items-center justify-center hover:border-neon-500/30 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-void-400" />
          </Link>
          <div>
            <h1 className="font-display text-3xl font-bold text-white">
              All Reviews
            </h1>
            <p className="text-void-400 mt-1">
              {filteredReviews.length} of {reviews.length} reviews
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
          <input
            type="text"
            placeholder="Search reviews..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-void-800/50 border border-void-700/50 
                       rounded-xl text-white placeholder-void-500 focus:outline-none 
                       focus:border-neon-500/50 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-void-500" />
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-4 py-2.5 bg-void-800/50 border border-void-700/50 
                       rounded-xl text-white focus:outline-none focus:border-neon-500/50 
                       transition-colors cursor-pointer"
          >
            <option value="ALL">All Risk Levels</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="MINIMAL">Minimal</option>
          </select>
        </div>
      </div>

      {/* Reviews List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card-glass rounded-2xl p-6"
      >
        <div className="flex items-center gap-2 mb-6">
          <Clock className="w-5 h-5 text-neon-400" />
          <h2 className="font-display text-xl font-semibold text-white">
            Reviews
          </h2>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : filteredReviews.length === 0 ? (
          <EmptyState hasFilters={searchTerm !== '' || riskFilter !== 'ALL'} />
        ) : (
          <div className="space-y-3">
            {filteredReviews.map((review, index) => (
              <ReviewCard key={review.review_id} review={review} index={index} />
            ))}
          </div>
        )}
      </motion.div>
    </div>
  )
}

function ReviewCard({ review, index }: { review: Review; index: number }) {
  const riskColors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
    HIGH: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
    MINIMAL: 'bg-neon-500/20 text-neon-400 border-neon-500/30',
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.05, 0.5) }}
    >
      <Link
        to={`/review/${review.review_id}`}
        className="flex items-center justify-between p-4 rounded-xl bg-void-800/30
                   border border-void-700/50 hover:border-neon-500/30
                   transition-all duration-300 group"
      >
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-void-700/50 flex items-center justify-center">
            <Shield className="w-6 h-6 text-void-400 group-hover:text-neon-400 transition-colors" />
          </div>
          <div>
            <h3 className="font-medium text-white group-hover:text-neon-400 transition-colors">
              {review.title}
            </h3>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-sm text-void-400">
                {new Date(review.reviewed_at).toLocaleDateString()}
              </span>
              <span className="text-void-600">|</span>
              <span className="text-sm text-void-400">{review.findings_count} findings</span>
              {review.dimensions && review.dimensions.length > 0 && (
                <>
                  <span className="text-void-600">|</span>
                  <span className="text-sm text-aurora-400">
                    {review.dimensions.join(', ')}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${riskColors[review.risk_rating]}`}
          >
            {review.risk_rating}
          </span>
          <ArrowRight className="w-5 h-5 text-void-500 group-hover:text-neon-400 group-hover:translate-x-1 transition-all" />
        </div>
      </Link>
    </motion.div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full border-2 border-neon-500/30 border-t-neon-400 animate-spin" />
        <p className="text-void-400">Loading reviews...</p>
      </div>
    </div>
  )
}

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 mx-auto rounded-2xl bg-void-800/50 flex items-center justify-center mb-6">
        <Shield className="w-10 h-10 text-void-500" />
      </div>
      <h3 className="text-xl font-display font-semibold text-white mb-2">
        {hasFilters ? 'No matching reviews' : 'No reviews yet'}
      </h3>
      <p className="text-void-400 mb-8 max-w-md mx-auto">
        {hasFilters
          ? 'Try adjusting your search or filters'
          : 'Start your first product review to analyze your PRD against your codebase'}
      </p>
      {!hasFilters && (
        <Link to="/new" className="btn-primary inline-flex items-center gap-2">
          Create Review
        </Link>
      )}
    </div>
  )
}

