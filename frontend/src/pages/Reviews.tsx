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

interface Review {
  review_id: string
  title: string
  status: string
  risk_rating: string
  findings_count: number
  reviewed_at: string
}

export default function Reviews() {
  const [searchTerm, setSearchTerm] = useState('')
  const [riskFilter, setRiskFilter] = useState<string>('ALL')

  const { data: reviews = [], isLoading } = useQuery<Review[]>({
    queryKey: ['reviews'],
    queryFn: async () => {
      const res = await fetch('/api/reviews')
      if (!res.ok) throw new Error('Failed to fetch reviews')
      return res.json()
    },
  })

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch = review.title.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesRisk = riskFilter === 'ALL' || review.risk_rating === riskFilter
    return matchesSearch && matchesRisk
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="w-10 h-10 rounded-xl bg-surface-800/50 border border-surface-700 
                       flex items-center justify-center hover:border-primary-500/30 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-surface-400" />
          </Link>
          <div>
            <h1 className="font-display text-3xl font-bold text-white">
              All Reviews
            </h1>
            <p className="text-surface-400 mt-1">
              {filteredReviews.length} of {reviews.length} reviews
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
          <input
            type="text"
            placeholder="Search reviews..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-surface-800/50 border border-surface-700 
                       rounded-xl text-white placeholder-surface-500 focus:outline-none 
                       focus:border-primary-500/50 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-surface-500" />
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-4 py-2.5 bg-surface-800/50 border border-surface-700 
                       rounded-xl text-white focus:outline-none focus:border-primary-500/50 
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
        className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6"
      >
        <div className="flex items-center gap-2 mb-6">
          <Clock className="w-5 h-5 text-primary-400" />
          <h2 className="font-display text-xl font-semibold text-white">
            Reviews
          </h2>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : filteredReviews.length === 0 ? (
          <EmptyState hasFilters={searchTerm !== '' || riskFilter !== 'ALL'} />
        ) : (
          <div className="space-y-4">
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
    HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
    MINIMAL: 'bg-primary-500/20 text-primary-400 border-primary-500/30',
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.05, 0.5) }}
    >
      <Link
        to={`/review/${review.review_id}`}
        className="flex items-center justify-between p-4 rounded-xl bg-surface-800/50 
                   border border-surface-700 hover:border-primary-500/50 
                   transition-all duration-200 group"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-surface-700 flex items-center justify-center">
            <Shield className="w-5 h-5 text-surface-400 group-hover:text-primary-400 transition-colors" />
          </div>
          <div>
            <h3 className="font-medium text-white group-hover:text-primary-400 transition-colors">
              {review.title}
            </h3>
            <p className="text-sm text-surface-400">
              {new Date(review.reviewed_at).toLocaleDateString()} • {review.findings_count} findings
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${riskColors[review.risk_rating]}`}>
            {review.risk_rating}
          </span>
          <ArrowRight className="w-5 h-5 text-surface-500 group-hover:text-primary-400 
                                 group-hover:translate-x-1 transition-all" />
        </div>
      </Link>
    </motion.div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent" />
        <p className="text-surface-400">Loading reviews...</p>
      </div>
    </div>
  )
}

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="text-center py-16">
      <div className="w-16 h-16 mx-auto rounded-full bg-surface-800 flex items-center justify-center mb-4">
        <Shield className="w-8 h-8 text-surface-500" />
      </div>
      <h3 className="text-lg font-medium text-white mb-2">
        {hasFilters ? 'No matching reviews' : 'No reviews yet'}
      </h3>
      <p className="text-surface-400 mb-6">
        {hasFilters
          ? 'Try adjusting your search or filters'
          : 'Start your first product review to see results here'}
      </p>
      {!hasFilters && (
        <Link
          to="/new"
          className="inline-flex items-center gap-2 px-6 py-3 bg-primary-500 text-white 
                     font-medium rounded-lg hover:bg-primary-600 transition-colors"
        >
          Create Review
        </Link>
      )}
    </div>
  )
}

