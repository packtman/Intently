import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  ArrowRight,
  Activity,
  FileText,
  Code,
  Target,
  LayoutDashboard,
} from 'lucide-react'
import IntentBreakdown from '../components/IntentBreakdown'

interface Review {
  review_id: string
  title: string
  status: string
  risk_rating: string
  findings_count: number
  reviewed_at: string
}

type Tab = 'overview' | 'intent'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  const { data: reviews = [], isLoading } = useQuery<Review[]>({
    queryKey: ['reviews'],
    queryFn: async () => {
      const res = await fetch('/api/reviews')
      if (!res.ok) throw new Error('Failed to fetch reviews')
      return res.json()
    },
  })

  const stats = {
    total: reviews.length,
    critical: reviews.filter(r => r.risk_rating === 'CRITICAL').length,
    high: reviews.filter(r => r.risk_rating === 'HIGH').length,
    completed: reviews.filter(r => r.status === 'completed').length,
  }

  const tabs = [
    { id: 'overview' as Tab, label: 'Overview', icon: LayoutDashboard },
    { id: 'intent' as Tab, label: 'Intent Breakdown', icon: Target },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">
            Security Dashboard
          </h1>
          <p className="text-surface-400 mt-1">
            Monitor and manage security reviews
          </p>
        </div>
        <Link
          to="/new"
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 
                     text-white font-medium rounded-lg hover:from-primary-600 hover:to-primary-700 
                     transition-all duration-200 glow-primary"
        >
          <FileText className="w-5 h-5" />
          New Review
        </Link>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 p-1 bg-surface-900/50 rounded-xl border border-surface-800 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all duration-200
              ${activeTab === tab.id
                ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
                : 'text-surface-400 hover:text-white hover:bg-surface-800'
              }
            `}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' ? (
        <motion.div
          key="overview"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-8"
        >
          {/* Stats Grid */}
          <div className="grid grid-cols-4 gap-6">
            <StatCard
              icon={Shield}
              label="Total Reviews"
              value={stats.total}
              color="primary"
            />
            <StatCard
              icon={AlertTriangle}
              label="Critical Risk"
              value={stats.critical}
              color="red"
            />
            <StatCard
              icon={Activity}
              label="High Risk"
              value={stats.high}
              color="orange"
            />
            <StatCard
              icon={CheckCircle}
              label="Completed"
              value={stats.completed}
              color="green"
            />
          </div>

          {/* Recent Reviews */}
          <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-xl font-semibold text-white">
                Recent Reviews
              </h2>
              <Link 
                to="/reviews" 
                className="text-primary-400 hover:text-primary-300 flex items-center gap-1 text-sm"
              >
                View all <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent" />
              </div>
            ) : reviews.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-4">
                {reviews.slice(0, 5).map((review, index) => (
                  <ReviewCard key={review.review_id} review={review} index={index} />
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-3 gap-6">
            <QuickAction
              icon={FileText}
              title="Parse PRD"
              description="Extract intent from a product requirement document"
              href="/new?step=prd"
            />
            <QuickAction
              icon={Code}
              title="Analyze Codebase"
              description="Scan your codebase for security patterns"
              href="/new?step=codebase"
            />
            <QuickAction
              icon={Shield}
              title="Full Review"
              description="Complete security review with LLM analysis"
              href="/new"
            />
          </div>
        </motion.div>
      ) : (
        <motion.div
          key="intent"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <IntentBreakdown />
        </motion.div>
      )}
    </div>
  )
}

function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  color 
}: { 
  icon: typeof Shield
  label: string
  value: number
  color: string 
}) {
  const colorClasses: Record<string, string> = {
    primary: 'from-primary-500/20 to-primary-600/10 border-primary-500/30 text-primary-400',
    red: 'from-red-500/20 to-red-600/10 border-red-500/30 text-red-400',
    orange: 'from-orange-500/20 to-orange-600/10 border-orange-500/30 text-orange-400',
    green: 'from-green-500/20 to-green-600/10 border-green-500/30 text-green-400',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        bg-gradient-to-br ${colorClasses[color]} 
        rounded-xl border p-6 card-hover
      `}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-surface-400 text-sm">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
        </div>
        <Icon className={`w-10 h-10 ${colorClasses[color].split(' ').pop()}`} />
      </div>
    </motion.div>
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
      transition={{ delay: index * 0.1 }}
    >
      <Link
        to={`/review/${review.review_id}`}
        className="flex items-center justify-between p-4 rounded-xl bg-surface-800/50 
                   border border-surface-700 hover:border-primary-500/50 
                   transition-all duration-200 group"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-surface-700 flex items-center justify-center">
            <Shield className="w-5 h-5 text-surface-400" />
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

function EmptyState() {
  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 mx-auto rounded-full bg-surface-800 flex items-center justify-center mb-4">
        <Shield className="w-8 h-8 text-surface-500" />
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No reviews yet</h3>
      <p className="text-surface-400 mb-6">
        Start your first security review to see results here
      </p>
      <Link
        to="/new"
        className="inline-flex items-center gap-2 px-6 py-3 bg-primary-500 text-white 
                   font-medium rounded-lg hover:bg-primary-600 transition-colors"
      >
        <FileText className="w-5 h-5" />
        Create Review
      </Link>
    </div>
  )
}

function QuickAction({ 
  icon: Icon, 
  title, 
  description, 
  href 
}: { 
  icon: typeof Shield
  title: string
  description: string
  href: string
}) {
  return (
    <Link
      to={href}
      className="block p-6 rounded-xl bg-surface-900/50 border border-surface-800 
                 hover:border-primary-500/50 transition-all duration-200 group card-hover"
    >
      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary-500/20 to-accent-500/20 
                      flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <Icon className="w-6 h-6 text-primary-400" />
      </div>
      <h3 className="font-semibold text-white mb-2 group-hover:text-primary-400 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-surface-400">{description}</p>
    </Link>
  )
}
