/**
 * FindingValidationPanel - Allows team members to validate AI-generated findings
 *
 * This component is only rendered when the finding_validation feature is enabled.
 * It provides a UI for users to:
 * - Mark findings as validated, rejected, or needing discussion
 * - Add justification notes
 * - See validation history
 *
 * Feature flag: FEATURE_FINDING_VALIDATION=true
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle,
  XCircle,
  MessageSquare,
  Clock,
  Shield,
  AlertTriangle,
  Loader2,
  ChevronDown,
  User,
  Building2,
} from 'lucide-react'
import { api } from '../../services/api'
import type { Finding, FindingValidation, ValidateFindingRequest } from '../../types'

interface FindingValidationPanelProps {
  finding: Finding
  reviewId: string
  enabled: boolean
  onValidated?: () => void
  // Current user info (would come from auth in production)
  currentUserId?: string
  currentUserName?: string
  currentTeam?: string
}

type ValidationStatus = 'validated' | 'rejected' | 'needs_discussion' | 'accepted_risk' | 'deferred'

const statusConfig: Record<
  ValidationStatus,
  { label: string; icon: typeof CheckCircle; color: string; description: string }
> = {
  validated: {
    label: 'Validated',
    icon: CheckCircle,
    color: 'green',
    description: 'Finding is accurate and actionable',
  },
  rejected: {
    label: 'Rejected',
    icon: XCircle,
    color: 'red',
    description: 'False positive - not applicable',
  },
  needs_discussion: {
    label: 'Needs Discussion',
    icon: MessageSquare,
    color: 'yellow',
    description: 'Requires cross-team input',
  },
  accepted_risk: {
    label: 'Accepted Risk',
    icon: Shield,
    color: 'ember',
    description: 'Valid but accepted with justification',
  },
  deferred: {
    label: 'Deferred',
    icon: Clock,
    color: 'void',
    description: 'Valid but not in scope for now',
  },
}

export function FindingValidationPanel({
  finding,
  reviewId,
  enabled,
  onValidated,
  currentUserId = 'user-1',
  currentUserName = 'Current User',
  currentTeam = 'security',
}: FindingValidationPanelProps) {
  const queryClient = useQueryClient()
  const [selectedStatus, setSelectedStatus] = useState<ValidationStatus | ''>('')
  const [notes, setNotes] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)

  // Don't render if feature is disabled
  if (!enabled) return null

  // Fetch current validation status
  const { data: validation, isLoading: isLoadingValidation } = useQuery({
    queryKey: ['finding-validation', reviewId, finding.id],
    queryFn: () => api.getFindingValidation(reviewId, finding.id),
    enabled: enabled,
  })

  // Mutation to validate finding
  const validateMutation = useMutation({
    mutationFn: (request: ValidateFindingRequest) =>
      api.validateFinding(reviewId, finding.id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding-validation', reviewId, finding.id] })
      queryClient.invalidateQueries({ queryKey: ['review-validations', reviewId] })
      setSelectedStatus('')
      setNotes('')
      setIsExpanded(false)
      onValidated?.()
    },
  })

  const handleSubmit = () => {
    if (!selectedStatus) return

    validateMutation.mutate({
      status: selectedStatus,
      notes,
      validator_id: currentUserId,
      validator_team: currentTeam,
    })
  }

  const currentStatus = validation?.status || 'pending'
  const isValidated = currentStatus !== 'pending'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 rounded-xl border border-void-700 bg-void-800/30 overflow-hidden"
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-void-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isValidated
                ? statusConfig[currentStatus as ValidationStatus]?.color === 'green'
                  ? 'bg-green-500/20'
                  : statusConfig[currentStatus as ValidationStatus]?.color === 'red'
                    ? 'bg-red-500/20'
                    : statusConfig[currentStatus as ValidationStatus]?.color === 'yellow'
                      ? 'bg-yellow-500/20'
                      : 'bg-void-700'
                : 'bg-void-700'
            }`}
          >
            {isLoadingValidation ? (
              <Loader2 className="w-4 h-4 text-void-400 animate-spin" />
            ) : isValidated ? (
              (() => {
                const Icon = statusConfig[currentStatus as ValidationStatus]?.icon || Shield
                const color = statusConfig[currentStatus as ValidationStatus]?.color || 'void'
                const colorClass =
                  color === 'green'
                    ? 'text-green-400'
                    : color === 'red'
                      ? 'text-red-400'
                      : color === 'yellow'
                        ? 'text-yellow-400'
                        : 'text-void-400'
                return <Icon className={`w-4 h-4 ${colorClass}`} />
              })()
            ) : (
              <AlertTriangle className="w-4 h-4 text-void-400" />
            )}
          </div>
          <div className="text-left">
            <p className="text-sm font-medium text-white">
              {isValidated
                ? statusConfig[currentStatus as ValidationStatus]?.label || 'Validated'
                : 'Pending Validation'}
            </p>
            {isValidated && validation && 'validator_id' in validation && (
              <p className="text-xs text-void-400">
                by {validation.validator_team} team
              </p>
            )}
          </div>
        </div>
        <ChevronDown
          className={`w-5 h-5 text-void-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
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
              {/* Current validation info */}
              {isValidated && validation && 'notes' in validation && validation.notes && (
                <div className="p-3 rounded-lg bg-void-800/50">
                  <p className="text-xs text-void-400 mb-1">Validation Notes</p>
                  <p className="text-sm text-void-300">{validation.notes}</p>
                  {'validated_at' in validation && (
                    <p className="text-xs text-void-500 mt-2">
                      {new Date(validation.validated_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}

              {/* Status selection */}
              <div>
                <label className="block text-xs font-medium text-void-400 mb-2">
                  {isValidated ? 'Update Validation' : 'Validate Finding'}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.entries(statusConfig) as [ValidationStatus, typeof statusConfig['validated']][]).map(
                    ([status, config]) => {
                      const Icon = config.icon
                      const isSelected = selectedStatus === status
                      const colorClasses = {
                        green: isSelected
                          ? 'bg-green-500/20 border-green-500/50 text-green-400'
                          : 'hover:bg-green-500/10 hover:border-green-500/30',
                        red: isSelected
                          ? 'bg-red-500/20 border-red-500/50 text-red-400'
                          : 'hover:bg-red-500/10 hover:border-red-500/30',
                        yellow: isSelected
                          ? 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
                          : 'hover:bg-yellow-500/10 hover:border-yellow-500/30',
                        ember: isSelected
                          ? 'bg-ember-500/20 border-ember-500/50 text-ember-400'
                          : 'hover:bg-ember-500/10 hover:border-ember-500/30',
                        void: isSelected
                          ? 'bg-void-600 border-void-500 text-void-300'
                          : 'hover:bg-void-700 hover:border-void-600',
                      }

                      return (
                        <button
                          key={status}
                          onClick={() => setSelectedStatus(status)}
                          className={`
                            p-3 rounded-lg border border-void-700 text-left transition-all
                            ${isSelected ? colorClasses[config.color as keyof typeof colorClasses] : `text-void-400 ${colorClasses[config.color as keyof typeof colorClasses]}`}
                          `}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <Icon className="w-4 h-4" />
                            <span className="text-sm font-medium">{config.label}</span>
                          </div>
                          <p className="text-xs opacity-70">{config.description}</p>
                        </button>
                      )
                    }
                  )}
                </div>
              </div>

              {/* Notes input */}
              {selectedStatus && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                >
                  <label className="block text-xs font-medium text-void-400 mb-2">
                    Justification / Notes
                    {selectedStatus === 'rejected' && (
                      <span className="text-red-400 ml-1">(required for rejections)</span>
                    )}
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder={
                      selectedStatus === 'rejected'
                        ? 'Explain why this is a false positive...'
                        : selectedStatus === 'accepted_risk'
                          ? 'Explain why this risk is being accepted...'
                          : 'Add any additional context...'
                    }
                    className="w-full p-3 rounded-lg bg-void-800 border border-void-700 text-white text-sm placeholder:text-void-500 resize-none focus:outline-none focus:border-neon-500/50"
                    rows={3}
                  />
                </motion.div>
              )}

              {/* Validator info */}
              <div className="flex items-center gap-4 text-xs text-void-500">
                <div className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  <span>{currentUserName}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Building2 className="w-3 h-3" />
                  <span>{currentTeam} team</span>
                </div>
              </div>

              {/* Submit button */}
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setSelectedStatus('')
                    setNotes('')
                    setIsExpanded(false)
                  }}
                  className="px-4 py-2 text-sm text-void-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={
                    !selectedStatus ||
                    validateMutation.isPending ||
                    (selectedStatus === 'rejected' && !notes.trim())
                  }
                  className={`
                    px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${
                      selectedStatus && (selectedStatus !== 'rejected' || notes.trim())
                        ? 'bg-neon-500 text-void-950 hover:bg-neon-400'
                        : 'bg-void-700 text-void-500 cursor-not-allowed'
                    }
                  `}
                >
                  {validateMutation.isPending ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </span>
                  ) : (
                    'Save Validation'
                  )}
                </button>
              </div>

              {/* Error message */}
              {validateMutation.error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                  <p className="text-sm text-red-400">
                    {validateMutation.error instanceof Error
                      ? validateMutation.error.message
                      : 'Failed to save validation'}
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
 * ValidationStatusBadge - Compact badge showing validation status
 *
 * Use this in finding list views to show at-a-glance validation state
 */
export function ValidationStatusBadge({
  status,
  compact = false,
}: {
  status: string
  compact?: boolean
}) {
  if (status === 'pending') {
    return compact ? null : (
      <span className="px-2 py-0.5 rounded-full bg-void-700 text-void-400 text-xs">
        Pending
      </span>
    )
  }

  const config = statusConfig[status as ValidationStatus]
  if (!config) return null

  const Icon = config.icon
  const colorClasses = {
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    ember: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    void: 'bg-void-600 text-void-300 border-void-500',
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${colorClasses[config.color as keyof typeof colorClasses]}`}
    >
      <Icon className="w-3 h-3" />
      {!compact && config.label}
    </span>
  )
}

