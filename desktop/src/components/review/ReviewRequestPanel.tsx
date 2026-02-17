import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { GitPullRequest, CheckCircle, XCircle, Clock, AlertTriangle, Send, Users } from 'lucide-react'

interface Reviewer {
  id: string
  team: string
  user_id: string | null
  required: boolean
  status: 'pending' | 'approved' | 'changes_requested' | 'blocked'
  responded_at: string | null
  notes: string
}

interface ReviewRequestData {
  id: string
  review_id: string
  status: string
  title: string
  deadline: string | null
  reviewers: Reviewer[]
  progress: {
    total: number
    approved: number
    blocked: number
    changes_requested: number
    pending: number
    required_total: number
    required_approved: number
    all_required_approved: boolean
  }
}

interface ReviewRequestPanelProps {
  reviewId: string
}

const TEAM_OPTIONS = ['security', 'privacy', 'compliance', 'engineering', 'architecture']

const statusIcon = (status: string) => {
  switch (status) {
    case 'approved': return <CheckCircle className="w-4 h-4 text-green-400" />
    case 'blocked': return <XCircle className="w-4 h-4 text-red-400" />
    case 'changes_requested': return <AlertTriangle className="w-4 h-4 text-yellow-400" />
    default: return <Clock className="w-4 h-4 text-surface-400" />
  }
}

const statusColor = (status: string) => {
  switch (status) {
    case 'approved': return 'text-green-400 bg-green-500/10 border-green-500/30'
    case 'blocked': return 'text-red-400 bg-red-500/10 border-red-500/30'
    case 'changes_requested': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
    case 'open': return 'text-blue-400 bg-blue-500/10 border-blue-500/30'
    default: return 'text-surface-400 bg-surface-800 border-surface-700'
  }
}

export default function ReviewRequestPanel({ reviewId }: ReviewRequestPanelProps) {
  const [requestData, setRequestData] = useState<ReviewRequestData | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedTeams, setSelectedTeams] = useState<string[]>(['security'])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRequest()
  }, [reviewId])

  const fetchRequest = async () => {
    try {
      const res = await fetch(`/api/reviews/${reviewId}/review-request`)
      if (res.ok) {
        const data = await res.json()
        setRequestData(data)
      }
    } catch {}
  }

  const createRequest = async () => {
    if (selectedTeams.length === 0) return
    setIsSubmitting(true)
    setError(null)

    try {
      const res = await fetch(`/api/reviews/${reviewId}/request-review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requested_by: 'current-user',
          reviewers: selectedTeams.map(team => ({ team, required: true })),
        }),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || `HTTP ${res.status}`)
      }

      setShowCreateForm(false)
      fetchRequest()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  // No request exists — show create button
  if (!requestData) {
    return (
      <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-4">
        {!showCreateForm ? (
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 hover:bg-primary-500/30 transition-colors w-full justify-center"
          >
            <GitPullRequest className="w-4 h-4" />
            <span className="text-sm font-medium">Request Review</span>
          </button>
        ) : (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-primary-400" />
              Select Reviewers
            </h4>
            <div className="flex flex-wrap gap-2">
              {TEAM_OPTIONS.map(team => (
                <button
                  key={team}
                  onClick={() => setSelectedTeams(prev =>
                    prev.includes(team) ? prev.filter(t => t !== team) : [...prev, team]
                  )}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    selectedTeams.includes(team)
                      ? 'bg-primary-500/20 border-primary-500/40 text-primary-300'
                      : 'bg-surface-800 border-surface-600 text-surface-400 hover:border-surface-500'
                  }`}
                >
                  {team}
                </button>
              ))}
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <div className="flex gap-2">
              <button
                onClick={createRequest}
                disabled={selectedTeams.length === 0 || isSubmitting}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 disabled:opacity-50 text-white text-sm transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                {isSubmitting ? 'Submitting...' : 'Submit for Review'}
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-3 py-2 rounded-lg bg-surface-700 text-surface-300 text-sm hover:bg-surface-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Request exists — show status
  const { progress } = requestData
  const progressPct = progress.total > 0
    ? Math.round((progress.approved / progress.total) * 100)
    : 0

  return (
    <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitPullRequest className="w-4 h-4 text-primary-400" />
          <h4 className="text-sm font-semibold text-white">Review Request</h4>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${statusColor(requestData.status)}`}>
          {requestData.status}
        </span>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-surface-400 mb-1">
          <span>{progress.approved}/{progress.total} approved</span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progressPct}%` }}
            className="h-full bg-gradient-to-r from-primary-500 to-green-500 rounded-full"
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Reviewers */}
      <div className="space-y-1.5">
        {requestData.reviewers.map((reviewer) => (
          <div
            key={reviewer.id}
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
          >
            <div className="flex items-center gap-2">
              {statusIcon(reviewer.status)}
              <span className="text-sm text-white capitalize">{reviewer.team}</span>
              {reviewer.required && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400">required</span>
              )}
            </div>
            <span className={`text-xs capitalize ${
              reviewer.status === 'approved' ? 'text-green-400' :
              reviewer.status === 'blocked' ? 'text-red-400' :
              reviewer.status === 'changes_requested' ? 'text-yellow-400' :
              'text-surface-500'
            }`}>
              {reviewer.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
