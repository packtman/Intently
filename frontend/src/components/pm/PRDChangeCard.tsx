/**
 * PRD Change Card - Displays a single PRD change with diff-style view
 * 
 * Layout matches the design mockup:
 * - Checkbox + BLOCKER badge + Question title + count
 * - "Because: ..." reasoning with code references
 * - Code evidence box (collapsible)
 * - PRD diff view with file name and section
 * - Action buttons
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
  Code,
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
  const [showCodeEvidence, setShowCodeEvidence] = useState(true)

  const severityColors = {
    blocker: 'bg-red-500/20 border-red-500/50 text-red-400',
    likely: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
    possible: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
  }

  const handleAccept = () => {
    if (isEditing) {
      onAccept(change.id, editedText)
      setIsEditing(false)
    } else {
      onAccept(change.id)
    }
  }

  // Format file path for code evidence header
  const formatCodeLocation = (filePath: string, lineNumber: number | null) => {
    const fileName = filePath.split('/').pop() || filePath
    return lineNumber ? `${fileName}:${lineNumber}` : fileName
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-900/50 backdrop-blur-sm rounded-xl border border-surface-800 overflow-hidden"
    >
      {/* Header - Checkbox + Badge + Question + Count */}
      <div className="p-4 border-b border-surface-800">
        <div className="flex items-start gap-3">
          {/* Checkbox placeholder */}
          <div className="mt-1">
            <input
              type="checkbox"
              className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 
                       focus:ring-primary-500 focus:ring-offset-0"
            />
          </div>
          
          {/* Content */}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${severityColors[change.severity]}`}>
                {change.severity}
              </span>
              <h3 className="text-white font-medium text-lg flex-1">
                "{change.question || change.section}"
              </h3>
              <span className="text-sm text-surface-500">
                {index} of {total}
              </span>
            </div>
            
            {/* Reasoning with "Because:" prefix */}
            <p className="text-surface-400 text-sm">
              <span className="text-surface-300">Because:</span> {change.reasoning}
            </p>
          </div>
          
          {/* Expand/Collapse */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-surface-500 hover:text-white transition-colors mt-1"
          >
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Code Evidence Section */}
          {change.code_evidence && change.code_evidence.length > 0 && (
            <div className="bg-surface-950 rounded-lg border border-surface-800 overflow-hidden">
              <button
                onClick={() => setShowCodeEvidence(!showCodeEvidence)}
                className="w-full p-3 bg-surface-900 border-b border-surface-800 flex items-center justify-between hover:bg-surface-800 transition-colors"
              >
                <div className="flex items-center gap-2 text-sm text-surface-300">
                  <Code className="w-4 h-4" />
                  <span className="font-medium">
                    {change.code_evidence[0].file_path}
                    {change.code_evidence[0].line_number && (
                      <span className="text-surface-500">
                        :{change.code_evidence[0].line_number}
                        {change.code_evidence.length > 1 && `-${change.code_evidence[change.code_evidence.length - 1].line_number}`}
                      </span>
                    )}
                  </span>
                </div>
                {showCodeEvidence ? <ChevronUp className="w-4 h-4 text-surface-500" /> : <ChevronDown className="w-4 h-4 text-surface-500" />}
              </button>
              
              {showCodeEvidence && (
                <div className="p-4 font-mono text-sm overflow-x-auto">
                  {change.code_evidence.map((evidence, i) => (
                    <div key={i} className="mb-2 last:mb-0">
                      {evidence.code_snippet && (
                        <pre className="text-cyan-400 bg-surface-900/50 p-3 rounded">
                          <code>{evidence.code_snippet}</code>
                        </pre>
                      )}
                      {evidence.context && (
                        <p className="text-surface-500 text-xs mt-1 pl-3">{evidence.context}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* PRD Diff View */}
          <div className="bg-surface-950 rounded-lg border border-surface-800 overflow-hidden">
            <div className="p-3 bg-surface-900 border-b border-surface-800 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-surface-300">
                <FileCode className="w-4 h-4" />
                <span className="font-medium">{change.prd_file || 'PRD'}</span>
                <span className="px-2 py-0.5 bg-surface-700 rounded text-xs text-surface-400">
                  {change.section}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-surface-500">
                <span className="text-red-400">- {change.diff_hunks.filter(h => h.operation === 'remove').length}</span>
                <span className="text-green-400">+ {change.diff_hunks.filter(h => h.operation === 'add').length}</span>
              </div>
            </div>
            
            {/* Diff Content */}
            <div className="p-4 font-mono text-sm space-y-1">
              {change.diff_hunks.map((hunk, i) => (
                <div
                  key={i}
                  className={`
                    flex items-start gap-2 py-1 px-3 rounded
                    ${hunk.operation === 'add' ? 'text-green-400 bg-green-500/10' : ''}
                    ${hunk.operation === 'remove' ? 'text-red-400 bg-red-500/10' : ''}
                    ${hunk.operation === 'context' ? 'text-surface-500' : ''}
                  `}
                >
                  <span className="w-4 flex-shrink-0 text-surface-600 select-none">
                    {hunk.operation === 'add' ? '+' : hunk.operation === 'remove' ? '-' : ' '}
                  </span>
                  <span className={hunk.operation === 'remove' ? 'line-through' : ''}>
                    {hunk.content}
                  </span>
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
