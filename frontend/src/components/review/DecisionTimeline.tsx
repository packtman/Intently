import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Gavel, Plus, Search, CheckCircle, XCircle, AlertTriangle, ArrowRight } from 'lucide-react'

interface Decision {
  id: string
  review_id: string
  decision_type: string
  title: string
  rationale: string
  decided_by: string
  decided_by_team: string
  linked_finding_ids: string[]
  alternatives_considered: string[]
  created_at: string
}

interface DecisionTimelineProps {
  reviewId: string
}

const TYPE_ICONS: Record<string, typeof CheckCircle> = {
  accepted_risk: AlertTriangle,
  rejected_finding: XCircle,
  approved_prd: CheckCircle,
  scope_change: ArrowRight,
}

const TYPE_COLORS: Record<string, string> = {
  accepted_risk: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  rejected_finding: 'text-red-400 bg-red-500/10 border-red-500/20',
  approved_prd: 'text-green-400 bg-green-500/10 border-green-500/20',
  scope_change: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  deferred: 'text-surface-400 bg-surface-800 border-surface-700',
  escalated: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
}

export default function DecisionTimeline({ reviewId }: DecisionTimelineProps) {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [rationale, setRationale] = useState('')
  const [decisionType, setDecisionType] = useState('scope_change')

  useEffect(() => {
    fetchDecisions()
  }, [reviewId])

  const fetchDecisions = async () => {
    try {
      const res = await fetch(`/api/reviews/${reviewId}/decisions`)
      if (res.ok) setDecisions(await res.json())
    } catch {}
  }

  const addDecision = async () => {
    if (!title.trim()) return
    try {
      await fetch(`/api/reviews/${reviewId}/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision_type: decisionType,
          title: title.trim(),
          rationale: rationale.trim(),
          decided_by: 'current-user',
        }),
      })
      setTitle('')
      setRationale('')
      setShowForm(false)
      fetchDecisions()
    } catch {}
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Gavel className="w-4 h-4 text-primary-400" />
          Decision Log
        </h4>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-primary-400 hover:bg-primary-500/10 transition-colors"
        >
          <Plus className="w-3 h-3" />
          Add
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="bg-surface-800 border border-surface-700 rounded-lg p-3 space-y-2"
        >
          <select
            value={decisionType}
            onChange={e => setDecisionType(e.target.value)}
            className="w-full bg-surface-900 border border-surface-600 rounded-lg px-2 py-1.5 text-xs text-white"
          >
            <option value="scope_change">Scope Change</option>
            <option value="accepted_risk">Accepted Risk</option>
            <option value="rejected_finding">Rejected Finding</option>
            <option value="deferred">Deferred</option>
            <option value="escalated">Escalated</option>
          </select>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Decision title..."
            className="w-full bg-surface-900 border border-surface-600 rounded-lg px-2 py-1.5 text-xs text-white placeholder-surface-500"
          />
          <textarea
            value={rationale}
            onChange={e => setRationale(e.target.value)}
            placeholder="Rationale..."
            rows={2}
            className="w-full bg-surface-900 border border-surface-600 rounded-lg px-2 py-1.5 text-xs text-white placeholder-surface-500 resize-none"
          />
          <div className="flex gap-2">
            <button onClick={addDecision} className="flex-1 px-2 py-1.5 rounded-lg bg-primary-500 text-white text-xs hover:bg-primary-600">Save</button>
            <button onClick={() => setShowForm(false)} className="px-2 py-1.5 rounded-lg bg-surface-700 text-surface-300 text-xs hover:bg-surface-600">Cancel</button>
          </div>
        </motion.div>
      )}

      {/* Timeline */}
      {decisions.length === 0 ? (
        <p className="text-xs text-surface-500 text-center py-3">No decisions recorded yet.</p>
      ) : (
        <div className="relative pl-4 space-y-3">
          <div className="absolute left-1.5 top-2 bottom-2 w-px bg-surface-700" />
          {decisions.map((d, i) => {
            const Icon = TYPE_ICONS[d.decision_type] || Gavel
            const color = TYPE_COLORS[d.decision_type] || TYPE_COLORS.deferred
            return (
              <motion.div
                key={d.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="relative"
              >
                <div className={`absolute -left-4 top-2 w-3 h-3 rounded-full border-2 ${color}`} />
                <div className="bg-surface-800 border border-surface-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-3.5 h-3.5 text-surface-400" />
                    <span className="text-xs font-medium text-white">{d.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${color}`}>
                      {d.decision_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  {d.rationale && <p className="text-[11px] text-surface-400 mt-1">{d.rationale}</p>}
                  <p className="text-[10px] text-surface-500 mt-1">
                    {d.decided_by} · {new Date(d.created_at).toLocaleString()}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
