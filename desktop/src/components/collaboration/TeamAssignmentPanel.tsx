/**
 * TeamAssignmentPanel - Assign findings to teams/users for review
 *
 * Routes findings to appropriate team queues based on dimension or manual selection.
 * Feature flag: FEATURE_TEAM_ASSIGNMENT=true
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users,
  UserPlus,
  Building2,
  ChevronDown,
  Check,
  Loader2,
  Shield,
  Eye,
  FileCheck,
  Code,
  Network,
  Clock,
} from 'lucide-react'
import { api } from '../../services/api'
import type { Finding, AssignFindingRequest, FindingAssignment } from '../../types'

interface TeamAssignmentPanelProps {
  finding: Finding
  reviewId: string
  enabled: boolean
  currentUserId?: string
  onAssigned?: () => void
}

// Team configuration with icons and colors
const teamConfig: Record<string, { 
  label: string
  icon: typeof Shield
  color: string
  description: string 
}> = {
  security: {
    label: 'Security',
    icon: Shield,
    color: 'cyan',
    description: 'Security vulnerabilities and threats',
  },
  privacy: {
    label: 'Privacy',
    icon: Eye,
    color: 'aurora',
    description: 'Data protection and PII concerns',
  },
  compliance: {
    label: 'Compliance',
    icon: FileCheck,
    color: 'ember',
    description: 'Regulatory and policy compliance',
  },
  engineering: {
    label: 'Engineering',
    icon: Code,
    color: 'green',
    description: 'Technical implementation issues',
  },
  architecture: {
    label: 'Architecture',
    icon: Network,
    color: 'purple',
    description: 'System design and scalability',
  },
  legal: {
    label: 'Legal',
    icon: FileCheck,
    color: 'slate',
    description: 'Legal review and contracts',
  },
}

const colorClasses: Record<string, { bg: string; text: string; border: string }> = {
  cyan: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', border: 'border-cyan-500/30' },
  aurora: { bg: 'bg-aurora-500/20', text: 'text-aurora-400', border: 'border-aurora-500/30' },
  ember: { bg: 'bg-ember-500/20', text: 'text-ember-400', border: 'border-ember-500/30' },
  green: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  purple: { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  slate: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30' },
}

export function TeamAssignmentPanel({
  finding,
  reviewId,
  enabled,
  currentUserId = 'user-1',
  onAssigned,
}: TeamAssignmentPanelProps) {
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<string>('')

  // Don't render if feature is disabled
  if (!enabled) return null

  // Fetch current assignments for review
  const { data: assignments } = useQuery({
    queryKey: ['review-assignments', reviewId],
    queryFn: () => api.getReviewAssignments(reviewId),
    enabled: enabled,
  })

  const currentAssignment = assignments?.assignments?.[finding.id]

  // Assign mutation
  const assignMutation = useMutation({
    mutationFn: (request: AssignFindingRequest) =>
      api.assignFinding(reviewId, finding.id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-assignments', reviewId] })
      setSelectedTeam('')
      setIsExpanded(false)
      onAssigned?.()
    },
  })

  const handleAssign = () => {
    if (!selectedTeam) return

    assignMutation.mutate({
      team: selectedTeam,
      assigned_by: currentUserId,
    })
  }

  // Suggest team based on finding dimension
  const suggestedTeam = finding.dimension || 'security'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 rounded-xl border border-void-700 bg-void-800/30 overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-void-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            currentAssignment 
              ? colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].bg
              : 'bg-void-700'
          }`}>
            {currentAssignment ? (
              (() => {
                const Icon = teamConfig[currentAssignment.team]?.icon || Users
                return <Icon className={`w-4 h-4 ${colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].text}`} />
              })()
            ) : (
              <Users className="w-4 h-4 text-void-400" />
            )}
          </div>
          <div className="text-left">
            <p className="text-sm font-medium text-white">
              {currentAssignment ? 'Assigned' : 'Team Assignment'}
            </p>
            {currentAssignment ? (
              <p className="text-xs text-void-400">
                {teamConfig[currentAssignment.team]?.label || currentAssignment.team} team
              </p>
            ) : (
              <p className="text-xs text-void-400">Route to team queue</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {currentAssignment && (
            <span className={`px-2 py-0.5 rounded-full text-xs ${
              colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].bg
            } ${colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].text}`}>
              {teamConfig[currentAssignment.team]?.label || currentAssignment.team}
            </span>
          )}
          <ChevronDown
            className={`w-5 h-5 text-void-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 pt-0 space-y-4 border-t border-void-700">
              {/* Current assignment info */}
              {currentAssignment && (
                <div className={`p-3 rounded-lg ${
                  colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].bg
                } border ${colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].border}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Check className={`w-4 h-4 ${colorClasses[teamConfig[currentAssignment.team]?.color || 'slate'].text}`} />
                      <span className="text-sm text-white">
                        Assigned to {teamConfig[currentAssignment.team]?.label || currentAssignment.team}
                      </span>
                    </div>
                    <span className="text-xs text-void-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(currentAssignment.assigned_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              )}

              {/* Team selection */}
              <div>
                <label className="block text-xs font-medium text-void-400 mb-2">
                  {currentAssignment ? 'Reassign to' : 'Assign to Team'}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(teamConfig).map(([team, config]) => {
                    const Icon = config.icon
                    const isSelected = selectedTeam === team
                    const isSuggested = team === suggestedTeam
                    const colors = colorClasses[config.color]

                    return (
                      <button
                        key={team}
                        onClick={() => setSelectedTeam(team)}
                        className={`
                          p-3 rounded-lg border text-left transition-all relative
                          ${isSelected 
                            ? `${colors.bg} ${colors.border} ${colors.text}` 
                            : `border-void-700 text-void-400 hover:${colors.bg} hover:${colors.border}`
                          }
                        `}
                      >
                        {isSuggested && !isSelected && (
                          <span className="absolute -top-2 -right-2 px-1.5 py-0.5 rounded text-[10px] bg-neon-500 text-void-950">
                            Suggested
                          </span>
                        )}
                        <div className="flex items-center gap-2 mb-1">
                          <Icon className="w-4 h-4" />
                          <span className="text-sm font-medium">{config.label}</span>
                        </div>
                        <p className="text-xs opacity-70">{config.description}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Submit button */}
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setSelectedTeam('')
                    setIsExpanded(false)
                  }}
                  className="px-4 py-2 text-sm text-void-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssign}
                  disabled={!selectedTeam || assignMutation.isPending}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${
                      selectedTeam
                        ? 'bg-neon-500 text-void-950 hover:bg-neon-400'
                        : 'bg-void-700 text-void-500 cursor-not-allowed'
                    }
                  `}
                >
                  {assignMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <UserPlus className="w-4 h-4" />
                  )}
                  {currentAssignment ? 'Reassign' : 'Assign'}
                </button>
              </div>

              {/* Error message */}
              {assignMutation.error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                  <p className="text-sm text-red-400">
                    {assignMutation.error instanceof Error
                      ? assignMutation.error.message
                      : 'Failed to assign finding'}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

/**
 * AssignmentBadge - Compact badge showing team assignment
 */
export function AssignmentBadge({ team }: { team: string }) {
  const config = teamConfig[team]
  if (!config) return null

  const Icon = config.icon
  const colors = colorClasses[config.color]

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${colors.bg} ${colors.text} ${colors.border}`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  )
}

