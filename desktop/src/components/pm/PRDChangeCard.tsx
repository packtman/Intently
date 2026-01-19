/**
 * PRD Change Card - Displays a single PRD change with diff-style view
 * 
 * Shows current state (red) vs suggested change (green) with accept/reject/edit actions
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Check,
  X,
  Edit,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  FileCode,
  Columns,
} from 'lucide-react'
import type { PRDChange } from '../../types'

interface PRDChangeCardProps {
  change: PRDChange
  index: number
  total: number
  onAccept: (changeId: string, editedText?: string) => void
  onReject: (changeId: string) => void
  onAskExpert?: (changeId: string) => void
  onViewDiff?: (change: PRDChange) => void
  isAccepting?: boolean
  isRejecting?: boolean
}

export function PRDChangeCard({
  change,
  index,
  total,
  onAccept,
  onReject,
  onAskExpert,
  onViewDiff,
  isAccepting = false,
  isRejecting = false,
}: PRDChangeCardProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [editedText, setEditedText] = useState(change.suggested_text)
  const [showCodeEvidence, setShowCodeEvidence] = useState(false)

  const severityColors = {
    blocker: 'bg-red-500/20 border-red-500/50 text-red-400',
    likely: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
    possible: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
  }

  const teamColors: Record<string, string> = {
    engineering: 'bg-green-500/20 text-green-400',
    security: 'bg-red-500/20 text-red-400',
    privacy: 'bg-purple-500/20 text-purple-400',
    compliance: 'bg-blue-500/20 text-blue-400',
    infrastructure: 'bg-orange-500/20 text-orange-400',
  }

  const handleAccept = () => {
    if (isEditing) {
      onAccept(change.id, editedText)
      setIsEditing(false)
    } else {
      onAccept(change.id)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-900/50 backdrop-blur-sm rounded-xl border border-surface-800 overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-surface-800">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className={`px-2 py-1 rounded text-xs font-medium ${severityColors[change.severity]}`}>
                {change.severity.toUpperCase()}
              </span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${teamColors[change.team] || 'bg-surface-700'}`}>
                {change.team}
              </span>
              <span className="text-sm text-surface-500">
                {index} of {total}
              </span>
            </div>
            <h3 className="text-white font-medium">{change.section}</h3>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-surface-500 hover:text-white transition-colors"
          >
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Reasoning */}
          <div className="text-sm text-surface-300">
            <p className="font-medium text-surface-200 mb-1">Why this change?</p>
            <p>{change.reasoning}</p>
          </div>

          {/* Diff View */}
          <div className="bg-surface-950 rounded-lg border border-surface-800 overflow-hidden">
            <div className="p-3 bg-surface-900 border-b border-surface-800">
              <div className="flex items-center gap-2 text-xs text-surface-400">
                <FileCode className="w-4 h-4" />
                <span>PRD Change ({change.change_type})</span>
              </div>
            </div>
            <div className="p-4 font-mono text-sm">
              {change.diff_hunks.map((hunk, i) => (
                <div
                  key={i}
                  className={`
                    ${hunk.operation === 'add' ? 'text-green-400 bg-green-500/10' : ''}
                    ${hunk.operation === 'remove' ? 'text-red-400 bg-red-500/10 line-through' : ''}
                    ${hunk.operation === 'context' ? 'text-surface-400' : ''}
                    py-1 px-2 rounded
                  `}
                >
                  <span className="mr-2 text-surface-600">
                    {hunk.operation === 'add' ? '+' : hunk.operation === 'remove' ? '-' : ' '}
                  </span>
                  {hunk.content}
                </div>
              ))}
            </div>
          </div>

          {/* Edit Mode */}
          {isEditing && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-surface-300">
                Edit before accepting:
              </label>
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg
                         text-white placeholder-surface-500 text-sm font-mono resize-none
                         focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                rows={6}
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2 border-t border-surface-800">
            <button
              onClick={handleAccept}
              disabled={isAccepting || isRejecting}
              className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-500/50
                       text-green-400 font-medium rounded-lg hover:bg-green-500/30
                       disabled:opacity-50 transition-all"
            >
              <Check className="w-4 h-4" />
              {isEditing ? 'Accept Edited' : 'Accept'}
            </button>
            {onViewDiff && (
              <button
                onClick={() => onViewDiff(change)}
                className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 border border-purple-500/50
                         text-purple-400 font-medium rounded-lg hover:bg-purple-500/30
                         transition-all"
              >
                <Columns className="w-4 h-4" />
                View Side-by-Side
              </button>
            )}
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="flex items-center gap-2 px-4 py-2 bg-surface-800 border border-surface-700
                       text-surface-300 font-medium rounded-lg hover:bg-surface-700
                       transition-all"
            >
              <Edit className="w-4 h-4" />
              {isEditing ? 'Cancel Edit' : 'Edit'}
            </button>
            <button
              onClick={() => onReject(change.id)}
              disabled={isAccepting || isRejecting}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-500/50
                       text-red-400 font-medium rounded-lg hover:bg-red-500/30
                       disabled:opacity-50 transition-all"
            >
              <X className="w-4 h-4" />
              Reject
            </button>
            {onAskExpert && (
              <button
                onClick={() => onAskExpert(change.id)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 border border-blue-500/50
                         text-blue-400 font-medium rounded-lg hover:bg-blue-500/30
                         transition-all ml-auto"
              >
                <MessageSquare className="w-4 h-4" />
                Ask Expert
              </button>
            )}
          </div>
        </div>
      )}
    </motion.div>
  )
}
