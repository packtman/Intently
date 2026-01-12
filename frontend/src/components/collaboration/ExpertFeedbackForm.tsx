/**
 * ExpertFeedbackForm - Capture expert corrections to AI-generated findings
 *
 * Enables experts to provide structured feedback that feeds into pattern learning.
 * Feature flag: FEATURE_EXPERT_FEEDBACK=true
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lightbulb,
  Target,
  AlertTriangle,
  MessageCircle,
  ChevronDown,
  Loader2,
  CheckCircle,
  ArrowRight,
  Clock,
  User,
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react'
import { api } from '../../services/api'
import type { Finding, ExpertFeedback } from '../../types'

interface ExpertFeedbackFormProps {
  finding: Finding
  reviewId: string
  enabled: boolean
  currentUserId?: string
  currentUserName?: string
  currentTeam?: string
  onFeedbackSubmitted?: () => void
}

type FeedbackType = 'accuracy' | 'severity' | 'recommendation' | 'context'

const feedbackTypeConfig: Record<FeedbackType, {
  label: string
  icon: typeof Target
  color: string
  description: string
  placeholder: string
}> = {
  accuracy: {
    label: 'Accuracy',
    icon: Target,
    color: 'red',
    description: 'Finding correctness - is this a real issue?',
    placeholder: 'e.g., "Not applicable - this endpoint uses token auth, not cookies"',
  },
  severity: {
    label: 'Severity',
    icon: AlertTriangle,
    color: 'orange',
    description: 'Risk level assessment - too high or too low?',
    placeholder: 'e.g., "Should be HIGH due to external exposure"',
  },
  recommendation: {
    label: 'Recommendation',
    icon: Lightbulb,
    color: 'green',
    description: 'Suggested fix quality - better approach?',
    placeholder: 'e.g., "Consider rate limiting instead of blocking"',
  },
  context: {
    label: 'Missing Context',
    icon: MessageCircle,
    color: 'blue',
    description: 'Information the AI missed',
    placeholder: 'e.g., "This service runs in an isolated VPC with no external access"',
  },
}

const colorClasses: Record<string, { bg: string; text: string; border: string }> = {
  red: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
  orange: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
  green: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  blue: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
}

const severityOptions = ['critical', 'high', 'medium', 'low', 'info']

export function ExpertFeedbackForm({
  finding,
  reviewId,
  enabled,
  currentUserId = 'user-1',
  currentUserName = 'Current User',
  currentTeam = 'security',
  onFeedbackSubmitted,
}: ExpertFeedbackFormProps) {
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(false)
  const [feedbackType, setFeedbackType] = useState<FeedbackType | ''>('')
  const [expertValue, setExpertValue] = useState('')
  const [reasoning, setReasoning] = useState('')

  // Don't render if feature is disabled
  if (!enabled) return null

  // Fetch existing feedback for this finding
  const { data: existingFeedback = [], isLoading } = useQuery({
    queryKey: ['finding-feedback', reviewId, finding.id],
    queryFn: () => api.getFindingFeedback(reviewId, finding.id),
    enabled: enabled && isExpanded,
  })

  // Submit feedback mutation
  const submitMutation = useMutation({
    mutationFn: (request: {
      feedback_type: FeedbackType
      original_value: string
      expert_value: string
      expert_id: string
      expert_team: string
      reasoning: string
    }) => api.submitExpertFeedback(reviewId, finding.id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding-feedback', reviewId, finding.id] })
      setFeedbackType('')
      setExpertValue('')
      setReasoning('')
      onFeedbackSubmitted?.()
    },
  })

  const handleSubmit = () => {
    if (!feedbackType || !expertValue.trim() || !reasoning.trim()) return

    // Determine original value based on feedback type
    let originalValue = ''
    switch (feedbackType) {
      case 'accuracy':
        originalValue = 'valid finding'
        break
      case 'severity':
        originalValue = finding.severity
        break
      case 'recommendation':
        originalValue = finding.recommendation
        break
      case 'context':
        originalValue = 'no additional context'
        break
    }

    submitMutation.mutate({
      feedback_type: feedbackType,
      original_value: originalValue,
      expert_value: expertValue.trim(),
      expert_id: currentUserId,
      expert_team: currentTeam,
      reasoning: reasoning.trim(),
    })
  }

  const feedbackCount = existingFeedback.length

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 rounded-xl border border-surface-700 bg-surface-800/30 overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
            <Lightbulb className="w-4 h-4 text-primary-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium text-white">
              Expert Feedback
              {feedbackCount > 0 && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-xs">
                  {feedbackCount}
                </span>
              )}
            </p>
            <p className="text-xs text-surface-400">
              Help improve AI analysis accuracy
            </p>
          </div>
        </div>
        <ChevronDown
          className={`w-5 h-5 text-surface-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
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
            <div className="p-4 pt-0 space-y-4 border-t border-surface-700">
              {/* Existing feedback */}
              {isLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 text-surface-400 animate-spin" />
                </div>
              ) : existingFeedback.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-surface-400">Previous Feedback</p>
                  {existingFeedback.map((fb) => (
                    <FeedbackItem key={fb.id} feedback={fb} />
                  ))}
                </div>
              )}

              {/* Feedback type selection */}
              <div>
                <label className="block text-xs font-medium text-surface-400 mb-2">
                  What would you like to correct?
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.entries(feedbackTypeConfig) as [FeedbackType, typeof feedbackTypeConfig['accuracy']][]).map(
                    ([type, config]) => {
                      const Icon = config.icon
                      const isSelected = feedbackType === type
                      const colors = colorClasses[config.color]

                      return (
                        <button
                          key={type}
                          onClick={() => {
                            setFeedbackType(type)
                            setExpertValue('')
                          }}
                          className={`
                            p-3 rounded-lg border text-left transition-all
                            ${isSelected 
                              ? `${colors.bg} ${colors.border} ${colors.text}` 
                              : `border-surface-700 text-surface-400 hover:${colors.bg} hover:${colors.border}`
                            }
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

              {/* Expert value input */}
              {feedbackType && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="space-y-4"
                >
                  {/* Show original value */}
                  <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700">
                    <p className="text-xs text-surface-400 mb-1">Current AI Assessment</p>
                    <p className="text-sm text-white">
                      {feedbackType === 'accuracy' && 'Valid finding requiring attention'}
                      {feedbackType === 'severity' && (
                        <span className="flex items-center gap-2">
                          Severity: <span className="font-medium uppercase">{finding.severity}</span>
                        </span>
                      )}
                      {feedbackType === 'recommendation' && finding.recommendation}
                      {feedbackType === 'context' && 'No additional context provided'}
                    </p>
                  </div>

                  {/* Expert correction */}
                  <div>
                    <label className="block text-xs font-medium text-surface-400 mb-2">
                      Your Expert Assessment
                    </label>
                    
                    {feedbackType === 'accuracy' && (
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => setExpertValue('false_positive')}
                          className={`p-3 rounded-lg border text-left transition-all ${
                            expertValue === 'false_positive'
                              ? 'bg-green-500/20 border-green-500/30 text-green-400'
                              : 'border-surface-700 text-surface-400 hover:bg-green-500/10'
                          }`}
                        >
                          <CheckCircle className="w-4 h-4 mb-1" />
                          <span className="text-sm font-medium">False Positive</span>
                          <p className="text-xs opacity-70">Not an actual issue</p>
                        </button>
                        <button
                          onClick={() => setExpertValue('not_applicable')}
                          className={`p-3 rounded-lg border text-left transition-all ${
                            expertValue === 'not_applicable'
                              ? 'bg-blue-500/20 border-blue-500/30 text-blue-400'
                              : 'border-surface-700 text-surface-400 hover:bg-blue-500/10'
                          }`}
                        >
                          <Minus className="w-4 h-4 mb-1" />
                          <span className="text-sm font-medium">Not Applicable</span>
                          <p className="text-xs opacity-70">Doesn't apply here</p>
                        </button>
                      </div>
                    )}

                    {feedbackType === 'severity' && (
                      <div className="flex flex-wrap gap-2">
                        {severityOptions.map((sev) => (
                          <button
                            key={sev}
                            onClick={() => setExpertValue(sev)}
                            className={`
                              flex items-center gap-2 px-4 py-2 rounded-lg border transition-all
                              ${expertValue === sev
                                ? 'bg-primary-500/20 border-primary-500/30 text-primary-400'
                                : 'border-surface-700 text-surface-400 hover:bg-surface-700'
                              }
                              ${sev === finding.severity ? 'opacity-50' : ''}
                            `}
                            disabled={sev === finding.severity}
                          >
                            {sev === finding.severity ? (
                              <span className="text-xs">(current)</span>
                            ) : severityOptions.indexOf(sev) < severityOptions.indexOf(finding.severity) ? (
                              <TrendingUp className="w-3 h-3" />
                            ) : (
                              <TrendingDown className="w-3 h-3" />
                            )}
                            <span className="text-sm font-medium uppercase">{sev}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    {(feedbackType === 'recommendation' || feedbackType === 'context') && (
                      <textarea
                        value={expertValue}
                        onChange={(e) => setExpertValue(e.target.value)}
                        placeholder={feedbackTypeConfig[feedbackType].placeholder}
                        className="w-full p-3 rounded-lg bg-surface-800 border border-surface-700 text-white text-sm placeholder:text-surface-500 resize-none focus:outline-none focus:border-primary-500/50"
                        rows={3}
                      />
                    )}
                  </div>

                  {/* Reasoning (required) */}
                  <div>
                    <label className="block text-xs font-medium text-surface-400 mb-2">
                      Reasoning <span className="text-red-400">*</span>
                    </label>
                    <textarea
                      value={reasoning}
                      onChange={(e) => setReasoning(e.target.value)}
                      placeholder="Explain why you're making this correction. This helps train better AI analysis..."
                      className="w-full p-3 rounded-lg bg-surface-800 border border-surface-700 text-white text-sm placeholder:text-surface-500 resize-none focus:outline-none focus:border-primary-500/50"
                      rows={3}
                    />
                  </div>

                  {/* Expert info */}
                  <div className="flex items-center gap-4 text-xs text-surface-500">
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
                        setFeedbackType('')
                        setExpertValue('')
                        setReasoning('')
                      }}
                      className="px-4 py-2 text-sm text-surface-400 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmit}
                      disabled={!expertValue.trim() || !reasoning.trim() || submitMutation.isPending}
                      className={`
                        flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                        ${
                          expertValue.trim() && reasoning.trim()
                            ? 'bg-primary-500 text-white hover:bg-primary-400'
                            : 'bg-surface-700 text-surface-500 cursor-not-allowed'
                        }
                      `}
                    >
                      {submitMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Lightbulb className="w-4 h-4" />
                      )}
                      Submit Feedback
                    </button>
                  </div>
                </motion.div>
              )}

              {/* Error message */}
              {submitMutation.error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                  <p className="text-sm text-red-400">
                    {submitMutation.error instanceof Error
                      ? submitMutation.error.message
                      : 'Failed to submit feedback'}
                  </p>
                </div>
              )}

              {/* Success message */}
              {submitMutation.isSuccess && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-3 rounded-lg bg-green-500/10 border border-green-500/30"
                >
                  <p className="text-sm text-green-400 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Feedback submitted - thank you for improving our AI!
                  </p>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function FeedbackItem({ feedback }: { feedback: ExpertFeedback }) {
  const config = feedbackTypeConfig[feedback.feedback_type as FeedbackType]
  if (!config) return null

  const Icon = config.icon
  const colors = colorClasses[config.color]

  return (
    <div className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${colors.text}`} />
          <span className={`text-sm font-medium ${colors.text}`}>{config.label}</span>
        </div>
        <span className="text-xs text-surface-400 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {new Date(feedback.created_at).toLocaleDateString()}
        </span>
      </div>
      <div className="flex items-center gap-2 text-sm mb-2">
        <span className="text-surface-400 line-through">{feedback.original_value}</span>
        <ArrowRight className="w-3 h-3 text-surface-500" />
        <span className="text-white font-medium">{feedback.expert_value}</span>
      </div>
      <p className="text-xs text-surface-300">{feedback.reasoning}</p>
      <div className="mt-2 flex items-center gap-2 text-xs text-surface-500">
        <User className="w-3 h-3" />
        <span>{feedback.expert_team} team</span>
      </div>
    </div>
  )
}

/**
 * FeedbackCountBadge - Shows number of expert corrections
 */
export function FeedbackCountBadge({ count }: { count: number }) {
  if (count === 0) return null

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-xs">
      <Lightbulb className="w-3 h-3" />
      {count}
    </span>
  )
}

