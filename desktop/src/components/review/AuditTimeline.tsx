import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ClipboardList, CheckCircle, XCircle, MessageSquare, UserPlus,
  GitPullRequest, Shield, Download, Filter, FileText
} from 'lucide-react'

interface AuditEntry {
  id: string
  timestamp: string
  review_id: string
  action: string
  actor: string
  actor_team: string | null
  target_type: string | null
  target_id: string | null
  details: Record<string, any>
}

interface AuditTimelineProps {
  reviewId: string
}

const ACTION_CONFIG: Record<string, { icon: typeof Shield; color: string; label: string }> = {
  review_created: { icon: FileText, color: 'text-blue-400', label: 'Review Created' },
  review_completed: { icon: CheckCircle, color: 'text-green-400', label: 'Review Completed' },
  finding_validated: { icon: CheckCircle, color: 'text-green-400', label: 'Finding Validated' },
  finding_assigned: { icon: UserPlus, color: 'text-blue-400', label: 'Finding Assigned' },
  comment_added: { icon: MessageSquare, color: 'text-purple-400', label: 'Comment Added' },
  feedback_submitted: { icon: Shield, color: 'text-orange-400', label: 'Feedback Submitted' },
  lifecycle_changed: { icon: GitPullRequest, color: 'text-cyan-400', label: 'Lifecycle Changed' },
  consensus_vote: { icon: CheckCircle, color: 'text-green-400', label: 'Consensus Vote' },
  review_request_created: { icon: GitPullRequest, color: 'text-blue-400', label: 'Review Requested' },
  review_request_responded: { icon: CheckCircle, color: 'text-green-400', label: 'Review Responded' },
  decision_logged: { icon: ClipboardList, color: 'text-yellow-400', label: 'Decision Logged' },
  prd_change_accepted: { icon: CheckCircle, color: 'text-green-400', label: 'PRD Change Accepted' },
  prd_change_rejected: { icon: XCircle, color: 'text-red-400', label: 'PRD Change Rejected' },
}

export default function AuditTimeline({ reviewId }: AuditTimelineProps) {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState<string>('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    fetchAuditLog()
  }, [reviewId, actionFilter])

  const fetchAuditLog = async () => {
    setLoading(true)
    try {
      const url = actionFilter
        ? `/api/audit/reviews/${reviewId}?action=${actionFilter}`
        : `/api/audit/reviews/${reviewId}`
      const res = await fetch(url)
      if (res.ok) {
        setEntries(await res.json())
      }
    } catch {}
    setLoading(false)
  }

  const exportCSV = async () => {
    setExporting(true)
    try {
      const res = await fetch(`/api/audit/export?format=csv`)
      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'audit_log.csv'
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch {}
    setExporting(false)
  }

  const uniqueActions = [...new Set(entries.map(e => e.action))]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <ClipboardList className="w-4 h-4 text-primary-400" />
          Audit Trail
          <span className="text-xs text-surface-500">({entries.length} entries)</span>
        </h4>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            disabled={exporting}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-surface-400 hover:text-white hover:bg-surface-800 transition-colors"
          >
            <Download className="w-3 h-3" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter */}
      {uniqueActions.length > 1 && (
        <div className="flex items-center gap-1 flex-wrap">
          <Filter className="w-3 h-3 text-surface-500" />
          <button
            onClick={() => setActionFilter('')}
            className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
              !actionFilter ? 'bg-primary-500/20 text-primary-400' : 'text-surface-400 hover:text-white'
            }`}
          >
            All
          </button>
          {uniqueActions.map(action => (
            <button
              key={action}
              onClick={() => setActionFilter(actionFilter === action ? '' : action)}
              className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
                actionFilter === action ? 'bg-primary-500/20 text-primary-400' : 'text-surface-400 hover:text-white'
              }`}
            >
              {ACTION_CONFIG[action]?.label || action}
            </button>
          ))}
        </div>
      )}

      {/* Timeline */}
      {loading ? (
        <div className="flex justify-center py-6">
          <div className="animate-spin w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full" />
        </div>
      ) : entries.length === 0 ? (
        <p className="text-xs text-surface-500 text-center py-6">
          No audit entries yet. Actions will be logged as the review progresses.
        </p>
      ) : (
        <div className="relative pl-5 space-y-2">
          <div className="absolute left-2 top-2 bottom-2 w-px bg-surface-700" />
          {entries.map((entry, i) => {
            const config = ACTION_CONFIG[entry.action] || { icon: ClipboardList, color: 'text-surface-400', label: entry.action }
            const Icon = config.icon
            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i * 0.02, 0.5) }}
                className="relative"
              >
                <div className={`absolute -left-5 top-2.5 w-2.5 h-2.5 rounded-full border-2 bg-surface-900 ${config.color.replace('text-', 'border-')}`} />
                <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-surface-800/50 border border-surface-700/50 hover:bg-surface-800 transition-colors">
                  <Icon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${config.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white">{config.label}</span>
                      {entry.actor_team && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-surface-700 text-surface-400">{entry.actor_team}</span>
                      )}
                    </div>
                    <p className="text-[10px] text-surface-500">
                      by {entry.actor} · {new Date(entry.timestamp).toLocaleString()}
                    </p>
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <p className="text-[10px] text-surface-600 mt-0.5 truncate">
                        {JSON.stringify(entry.details).slice(0, 80)}
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
