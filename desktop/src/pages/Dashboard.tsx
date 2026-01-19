import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { useMemo } from 'react'
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  Activity,
  FileText,
  Code,
  Sparkles,
  Clock,
  Zap,
} from 'lucide-react'
import { api } from '../services/api'
import { useBackend } from '../hooks/useBackend'
import type { Review } from '../types'

// PERFORMANCE: Hook to detect if user prefers reduced motion
function useAnimationConfig() {
  const shouldReduceMotion = useReducedMotion()
  
  return useMemo(() => ({
    // Disable animations if user prefers reduced motion
    animate: !shouldReduceMotion,
    transition: shouldReduceMotion ? { duration: 0 } : undefined,
  }), [shouldReduceMotion])
}

export default function Dashboard() {
  const { isConnected } = useBackend()
  const animConfig = useAnimationConfig()

  const { data: reviews = [], isLoading } = useQuery<Review[]>({
    queryKey: ['reviews'],
    queryFn: () => api.listReviews(),
    enabled: isConnected,
    // PERFORMANCE: Don't refetch on every mount, rely on stale time
    refetchOnMount: false,
  })

  const stats = {
    total: reviews.length,
    critical: reviews.filter((r) => r.risk_rating === 'CRITICAL').length,
    high: reviews.filter((r) => r.risk_rating === 'HIGH').length,
    completed: reviews.filter((r) => r.status === 'completed').length,
  }

  if (!isConnected) {
    return <OfflineState />
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-4xl font-bold text-white">
            Product Dashboard
          </h1>
          <p className="text-void-400 mt-2 text-lg">
            Monitor and manage your product feature reviews
          </p>
        </div>
        <Link to="/new" className="btn-primary flex items-center gap-2 no-drag">
          <Sparkles className="w-5 h-5" />
          New Review
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-6">
        <StatCard
          icon={Shield}
          label="Total Reviews"
          value={stats.total}
          color="neon"
          delay={0}
        />
        <StatCard
          icon={AlertTriangle}
          label="Critical Risk"
          value={stats.critical}
          color="red"
          delay={0.1}
        />
        <StatCard
          icon={Activity}
          label="High Risk"
          value={stats.high}
          color="ember"
          delay={0.2}
        />
        <StatCard
          icon={CheckCircle}
          label="Completed"
          value={stats.completed}
          color="green"
          delay={0.3}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-6">
        <QuickAction
          icon={FileText}
          title="Parse PRD"
          description="Extract intent from a product requirement document"
          href="/new?step=prd"
          color="neon"
        />
        <QuickAction
          icon={Code}
          title="Analyze Codebase"
          description="Scan your codebase for security patterns"
          href="/new?step=codebase"
          color="aurora"
        />
        <QuickAction
          icon={Shield}
          title="Full Review"
          description="Complete product review with AI analysis"
          href="/new"
          color="ember"
        />
      </div>

      {/* Recent Reviews */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card-glass rounded-2xl p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-display text-xl font-semibold text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-neon-400" />
            Recent Reviews
          </h2>
          {reviews.length > 5 && (
            <Link
              to="/reviews"
              className="text-neon-400 hover:text-neon-300 flex items-center gap-1 text-sm font-medium"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>

        {isLoading ? (
          <LoadingState />
        ) : reviews.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {reviews.slice(0, 5).map((review, index) => (
              <ReviewCard key={review.review_id} review={review} index={index} />
            ))}
          </div>
        )}
      </motion.div>
    </div>
  )
}

// PERFORMANCE: Memoize color classes to avoid recreating on every render
const statColorClasses: Record<string, { bg: string; border: string; icon: string; glow: string }> = {
  neon: {
    bg: 'from-neon-500/10 to-neon-600/5',
    border: 'border-neon-500/20',
    icon: 'text-neon-400',
    glow: 'shadow-neon-500/10',
  },
  red: {
    bg: 'from-red-500/10 to-red-600/5',
    border: 'border-red-500/20',
    icon: 'text-red-400',
    glow: 'shadow-red-500/10',
  },
  ember: {
    bg: 'from-ember-500/10 to-ember-600/5',
    border: 'border-ember-500/20',
    icon: 'text-ember-400',
    glow: 'shadow-ember-500/10',
  },
  green: {
    bg: 'from-green-500/10 to-green-600/5',
    border: 'border-green-500/20',
    icon: 'text-green-400',
    glow: 'shadow-green-500/10',
  },
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  delay,
}: {
  icon: typeof Shield
  label: string
  value: number
  color: string
  delay: number
}) {
  const shouldReduceMotion = useReducedMotion()
  const styles = statColorClasses[color]

  return (
    <motion.div
      initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={shouldReduceMotion ? { duration: 0 } : { delay }}
      className={`
        bg-gradient-to-br ${styles.bg} rounded-2xl border ${styles.border}
        p-6 shadow-lg ${styles.glow} card-hover
      `}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-void-400 text-sm font-medium">{label}</p>
          <p className="text-4xl font-display font-bold text-white mt-2">{value}</p>
        </div>
        <div className={`w-14 h-14 rounded-xl bg-void-800/50 flex items-center justify-center`}>
          <Icon className={`w-7 h-7 ${styles.icon}`} />
        </div>
      </div>
    </motion.div>
  )
}

function QuickAction({
  icon: Icon,
  title,
  description,
  href,
  color,
}: {
  icon: typeof Shield
  title: string
  description: string
  href: string
  color: string
}) {
  const colorClasses: Record<string, { from: string; to: string; hover: string }> = {
    neon: { from: 'from-neon-500/20', to: 'to-neon-600/10', hover: 'hover:border-neon-500/50' },
    aurora: { from: 'from-aurora-500/20', to: 'to-aurora-600/10', hover: 'hover:border-aurora-500/50' },
    ember: { from: 'from-ember-500/20', to: 'to-ember-600/10', hover: 'hover:border-ember-500/50' },
  }

  const styles = colorClasses[color]

  return (
    <Link
      to={href}
      className={`
        block p-6 rounded-2xl card-glass border border-void-700/50
        ${styles.hover} transition-all duration-300 group
      `}
    >
      <div
        className={`
          w-14 h-14 rounded-xl bg-gradient-to-br ${styles.from} ${styles.to}
          flex items-center justify-center mb-4 group-hover:scale-110 transition-transform
        `}
      >
        <Icon className="w-7 h-7 text-white" />
      </div>
      <h3 className="font-display font-semibold text-white text-lg mb-2 group-hover:text-neon-400 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-void-400 leading-relaxed">{description}</p>
    </Link>
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
      transition={{ delay: index * 0.1 }}
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

function EmptyState() {
  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 mx-auto rounded-2xl bg-void-800/50 flex items-center justify-center mb-6">
        <Shield className="w-10 h-10 text-void-500" />
      </div>
      <h3 className="text-xl font-display font-semibold text-white mb-2">No reviews yet</h3>
      <p className="text-void-400 mb-8 max-w-md mx-auto">
        Start your first product review to analyze your PRD against your codebase
      </p>
      <Link to="/new" className="btn-primary inline-flex items-center gap-2">
        <Sparkles className="w-5 h-5" />
        Create Review
      </Link>
    </div>
  )
}

function OfflineState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center"
      >
        <div className="w-24 h-24 mx-auto rounded-2xl bg-ember-500/10 border border-ember-500/30 flex items-center justify-center mb-6">
          <Zap className="w-12 h-12 text-ember-400" />
        </div>
        <h2 className="text-2xl font-display font-bold text-white mb-3">Backend Offline</h2>
        <p className="text-void-400 max-w-md mb-8">
          The Intently backend is not running. Configure the backend path in Settings
          and start the server to begin analyzing your code.
        </p>
        <div className="flex items-center gap-4 justify-center">
          <Link to="/settings" className="btn-primary">
            Open Settings
          </Link>
          <a
            href="https://github.com/context-graph/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            View Documentation
          </a>
        </div>
      </motion.div>
    </div>
  )
}
