/**
 * TeamQueuePage - View findings assigned to a specific team
 *
 * Shows all findings across reviews that are assigned to the team's queue.
 * Feature flag: FEATURE_TEAM_ASSIGNMENT=true
 */

import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Shield,
  Eye,
  FileCheck,
  Code,
  Network,
  AlertTriangle,
  Clock,
  ChevronRight,
  ArrowLeft,
  Inbox,
  Loader2,
  CheckCircle,
  Filter,
  Sparkles,
} from 'lucide-react'
import { useState } from 'react'
import { api } from '../services/api'
import type { CollaborationFeatures } from '../types'

// Team configuration
const teamConfig: Record<string, {
  label: string
  icon: typeof Shield
  color: string
  gradient: string
}> = {
  security: {
    label: 'Security',
    icon: Shield,
    color: 'cyan',
    gradient: 'from-cyan-500/20 to-cyan-600/10',
  },
  privacy: {
    label: 'Privacy',
    icon: Eye,
    color: 'purple',
    gradient: 'from-purple-500/20 to-purple-600/10',
  },
  compliance: {
    label: 'Compliance',
    icon: FileCheck,
    color: 'amber',
    gradient: 'from-amber-500/20 to-amber-600/10',
  },
  engineering: {
    label: 'Engineering',
    icon: Code,
    color: 'green',
    gradient: 'from-green-500/20 to-green-600/10',
  },
  architecture: {
    label: 'Architecture',
    icon: Network,
    color: 'orange',
    gradient: 'from-orange-500/20 to-orange-600/10',
  },
}

const colorClasses: Record<string, { bg: string; text: string; border: string }> = {
  cyan: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', border: 'border-cyan-500/30' },
  purple: { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  amber: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' },
  green: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  orange: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
}

const severityColors: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-green-500/20 text-green-400 border-green-500/30',
  info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
}

interface QueueItem {
  id: string
  finding_id: string
  review_id: string
  team: string
  user_id?: string
  assigned_by?: string
  assigned_at: string
  // Extended with finding details (would be populated by API in production)
  finding_title?: string
  finding_severity?: string
  finding_category?: string
  review_title?: string
}

export default function TeamQueuePage() {
  const { team } = useParams<{ team: string }>()
  const [severityFilter, setSeverityFilter] = useState<string | 'all'>('all')

  // Check if team assignment feature is enabled
  const { data: features, isLoading: loadingFeatures } = useQuery<CollaborationFeatures>({
    queryKey: ['collaboration-features'],
    queryFn: () => api.getCollaborationFeatures(),
    staleTime: 1000 * 60 * 5,
    retry: false,
  })

  // Fetch team queue
  const { data: queueItems = [], isLoading, error } = useQuery<QueueItem[]>({
    queryKey: ['team-queue', team],
    queryFn: async () => {
      const response = await fetch(`/api/collaboration/teams/${team}/queue`)
      if (!response.ok) throw new Error('Failed to fetch team queue')
      return response.json()
    },
    enabled: !!team && features?.team_assignment === true,
  })

  if (loadingFeatures) {
    return <LoadingState message="Loading..." />
  }

  if (!features?.team_assignment) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertTriangle className="w-16 h-16 text-yellow-400 mb-6" />
        <h2 className="text-xl font-semibold text-white mb-2">Feature Not Enabled</h2>
        <p className="text-surface-400 text-center max-w-md">
          Team assignment feature is not enabled. Set FEATURE_TEAM_ASSIGNMENT=true to enable team queues.
        </p>
        <Link
          to="/"
          className="mt-6 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-400 transition-colors"
        >
          Go to Dashboard
        </Link>
      </div>
    )
  }

  const config = teamConfig[team || ''] || {
    label: team || 'Unknown',
    icon: Shield,
    color: 'slate',
    gradient: 'from-slate-500/20 to-slate-600/10',
  }

  const TeamIcon = config.icon
  const colors = colorClasses[config.color] || colorClasses.cyan

  // Filter by severity
  const filteredItems = severityFilter === 'all'
    ? queueItems
    : queueItems.filter(item => item.finding_severity === severityFilter)

  // Group by severity for stats
  const severityStats = queueItems.reduce((acc, item) => {
    const sev = item.finding_severity || 'unknown'
    acc[sev] = (acc[sev] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/reviews"
            className="flex items-center gap-1 text-surface-400 hover:text-white transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Reviews
          </Link>
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${config.gradient} border ${colors.border} flex items-center justify-center`}>
              <TeamIcon className={`w-8 h-8 ${colors.text}`} />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold text-white">
                {config.label} Queue
              </h1>
              <p className="text-surface-400 mt-1">
                {queueItems.length} finding{queueItems.length !== 1 ? 's' : ''} awaiting review
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-5 gap-4">
        {['critical', 'high', 'medium', 'low', 'info'].map((severity) => (
          <motion.button
            key={severity}
            onClick={() => setSeverityFilter(severityFilter === severity ? 'all' : severity)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`
              p-4 rounded-xl border transition-all
              ${severityFilter === severity
                ? severityColors[severity]
                : 'bg-surface-800/50 border-surface-700 hover:border-surface-600'
              }
            `}
          >
            <p className="text-sm text-surface-400 capitalize">{severity}</p>
            <p className="text-2xl font-bold text-white mt-1">
              {severityStats[severity] || 0}
            </p>
          </motion.button>
        ))}
      </div>

      {/* Queue Content */}
      <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <Inbox className="w-5 h-5 text-surface-400" />
            Assigned Findings
            {severityFilter !== 'all' && (
              <span className={`px-2 py-0.5 rounded-full text-xs ${severityColors[severityFilter]}`}>
                {severityFilter.toUpperCase()}
              </span>
            )}
          </h2>
          {severityFilter !== 'all' && (
            <button
              onClick={() => setSeverityFilter('all')}
              className="text-sm text-surface-400 hover:text-white transition-colors flex items-center gap-1"
            >
              <Filter className="w-4 h-4" />
              Clear Filter
            </button>
          )}
        </div>

        {isLoading ? (
          <LoadingState message="Loading queue..." />
        ) : error ? (
          <ErrorState message="Failed to load team queue" />
        ) : filteredItems.length === 0 ? (
          <EmptyState
            message={severityFilter !== 'all' 
              ? `No ${severityFilter} severity findings in queue`
              : 'No findings assigned to this team yet'
            }
          />
        ) : (
          <div className="space-y-3">
            {filteredItems.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <QueueItemCard item={item} />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function QueueItemCard({ item }: { item: QueueItem }) {
  const severity = item.finding_severity || 'medium'
  
  return (
    <Link
      to={`/reviews/${item.review_id}#finding-${item.finding_id}`}
      className="block rounded-xl bg-surface-800/50 border border-surface-700 hover:border-surface-600 transition-all"
    >
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <span className={`px-2 py-1 rounded text-xs font-medium border ${severityColors[severity]}`}>
              {severity.toUpperCase()}
            </span>
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary-500/10 border border-primary-500/30">
              <Sparkles className="w-3 h-3 text-primary-400" />
              <span className="text-xs text-primary-400">AI</span>
            </span>
            <span className="text-white font-medium truncate">
              {item.finding_title || `Finding ${item.finding_id.slice(0, 8)}...`}
            </span>
          </div>
          <ChevronRight className="w-5 h-5 text-surface-400 flex-shrink-0" />
        </div>
        
        <div className="flex items-center gap-4 mt-3 text-xs text-surface-500">
          <span className="flex items-center gap-1">
            <FileCheck className="w-3 h-3" />
            {item.review_title || `Review ${item.review_id.slice(0, 8)}...`}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Assigned {formatRelativeTime(item.assigned_at)}
          </span>
          {item.finding_category && (
            <span className="px-2 py-0.5 rounded-full bg-surface-700">
              {item.finding_category}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Loader2 className="w-10 h-10 text-primary-400 animate-spin mb-4" />
      <p className="text-surface-400">{message}</p>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mb-4" />
      <p className="text-surface-400">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
      <p className="text-white font-medium">Queue Empty</p>
      <p className="text-surface-400 text-sm mt-1">{message}</p>
    </div>
  )
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}

