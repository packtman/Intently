/**
 * Bulk Accept Panel - Panel for selecting and accepting multiple PRD changes
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle2, Filter } from 'lucide-react'
import type { PRDChange } from '../../types'

interface BulkAcceptPanelProps {
  changes: PRDChange[]
  summary: {
    total: number
    by_team: Record<string, number>
    by_severity: Record<string, number>
  }
  onClose: () => void
  onBulkAccept: (changeIds?: string[], filter?: { teams?: string[]; severities?: string[] }) => void
}

export function BulkAcceptPanel({
  changes,
  summary,
  onClose,
  onBulkAccept,
}: BulkAcceptPanelProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [filterMode, setFilterMode] = useState<'none' | 'team' | 'severity'>('none')
  const [teamFilter, setTeamFilter] = useState<string[]>([])
  const [severityFilter, setSeverityFilter] = useState<string[]>([])

  const toggleSelection = (changeId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(changeId)) {
      newSelected.delete(changeId)
    } else {
      newSelected.add(changeId)
    }
    setSelectedIds(newSelected)
  }

  const selectAll = () => {
    setSelectedIds(new Set(changes.map((c) => c.id)))
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
  }

  const handleAccept = () => {
    if (filterMode === 'team' && teamFilter.length > 0) {
      onBulkAccept(undefined, { teams: teamFilter })
    } else if (filterMode === 'severity' && severityFilter.length > 0) {
      onBulkAccept(undefined, { severities: severityFilter })
    } else {
      onBulkAccept(selectedIds.size > 0 ? Array.from(selectedIds) : undefined)
    }
  }

  const teams = Object.keys(summary.by_team)
  const severities = Object.keys(summary.by_severity)

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-surface-900 rounded-2xl border border-surface-800 w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="p-6 border-b border-surface-800 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">Select Changes to Accept</h2>
              <p className="text-sm text-surface-400 mt-1">
                {selectedIds.size} of {changes.length} selected
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-surface-500 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Filters */}
          <div className="p-4 border-b border-surface-800 bg-surface-950">
            <div className="flex items-center gap-4 mb-4">
              <span className="text-sm text-surface-400 flex items-center gap-2">
                <Filter className="w-4 h-4" />
                Quick filters:
              </span>
              <button
                onClick={() => {
                  setFilterMode('none')
                  setSelectedIds(new Set(changes.map((c) => c.id)))
                }}
                className="px-3 py-1 text-sm rounded bg-surface-800 text-surface-300 hover:bg-surface-700"
              >
                All ({changes.length})
              </button>
              <button
                onClick={() => {
                  setFilterMode('severity')
                  setSeverityFilter(['blocker'])
                  setSelectedIds(new Set(changes.filter((c) => c.severity === 'blocker').map((c) => c.id)))
                }}
                className="px-3 py-1 text-sm rounded bg-red-500/20 text-red-400 border border-red-500/50"
              >
                Blockers ({summary.by_severity.blocker || 0})
              </button>
              {teams.map((team) => (
                <button
                  key={team}
                  onClick={() => {
                    setFilterMode('team')
                    setTeamFilter([team])
                    setSelectedIds(new Set(changes.filter((c) => c.team === team).map((c) => c.id)))
                  }}
                  className="px-3 py-1 text-sm rounded bg-surface-800 text-surface-300 hover:bg-surface-700 capitalize"
                >
                  {team} ({summary.by_team[team] || 0})
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={selectAll}
                className="text-sm text-primary-400 hover:text-primary-300"
              >
                Select All
              </button>
              <span className="text-surface-600">•</span>
              <button
                onClick={clearSelection}
                className="text-sm text-surface-400 hover:text-surface-300"
              >
                Clear Selection
              </button>
            </div>
          </div>

          {/* Changes List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {changes.map((change) => {
              const isSelected = selectedIds.has(change.id)
              return (
                <label
                  key={change.id}
                  className={`
                    flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                    ${isSelected
                      ? 'bg-primary-500/10 border-primary-500/50'
                      : 'bg-surface-800 border-surface-700 hover:border-surface-600'
                    }
                  `}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelection(change.id)}
                    className="mt-1 w-4 h-4 rounded border-surface-600 bg-surface-900
                             text-primary-500 focus:ring-primary-500 focus:ring-offset-surface-900"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-white">{change.section}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-surface-700 text-surface-300 capitalize">
                        {change.team}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                        change.severity === 'blocker' ? 'bg-red-500/20 text-red-400' :
                        change.severity === 'likely' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {change.severity}
                      </span>
                    </div>
                    <p className="text-sm text-surface-400 line-clamp-2">{change.reasoning}</p>
                  </div>
                </label>
              )
            })}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-surface-800 flex items-center justify-between">
            <div className="text-sm text-surface-400">
              {selectedIds.size} changes selected
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-surface-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAccept}
                disabled={selectedIds.size === 0 && filterMode === 'none'}
                className="flex items-center gap-2 px-6 py-2 bg-primary-500 text-white font-medium
                         rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all"
              >
                <CheckCircle2 className="w-4 h-4" />
                Accept Selected ({selectedIds.size || changes.length})
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
