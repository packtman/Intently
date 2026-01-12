/**
 * Effort Estimation Component
 * 
 * Displays code-grounded time estimates for PRD implementation
 */

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Clock, TrendingUp, Code2 } from 'lucide-react'
import { api } from '../../services/api'
import type { EffortEstimation as EffortEstimationType } from '../../types'

interface EffortEstimationProps {
  reviewId: string
}

export function EffortEstimation({ reviewId }: EffortEstimationProps) {
  const { data: estimation, isLoading } = useQuery({
    queryKey: ['effort-estimation', reviewId],
    queryFn: () => api.getEffortEstimation(reviewId),
    enabled: !!reviewId,
  })

  if (isLoading) {
    return (
      <div className="bg-surface-900/50 rounded-xl border border-surface-800 p-6">
        <div className="text-surface-400">Loading effort estimation...</div>
      </div>
    )
  }

  if (!estimation) {
    return null
  }

  const sprints = Math.ceil(estimation.total_days.likely / 10) // Assuming 2-week sprints

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-900/50 rounded-xl border border-surface-800 p-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <Clock className="w-5 h-5 text-primary-400" />
        <h3 className="text-lg font-semibold text-white">Effort Estimation</h3>
      </div>

      {/* TLDR */}
      <div className="mb-6 p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg">
        <div className="text-sm font-medium text-primary-400 mb-1">Summary</div>
        <div className="text-white">{estimation.tldr}</div>
      </div>

      {/* Time Range */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{estimation.total_days.min}</div>
          <div className="text-xs text-surface-400">Min Days</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-400">{estimation.total_days.likely}</div>
          <div className="text-xs text-surface-400">Likely Days</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-amber-400">{estimation.total_days.max}</div>
          <div className="text-xs text-surface-400">Max Days</div>
        </div>
      </div>

      {/* Codebase Support */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-sm text-surface-300">
            <Code2 className="w-4 h-4" />
            <span>Codebase Support</span>
          </div>
          <span className="text-sm font-medium text-white">{estimation.codebase_support.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-surface-800 rounded-full h-2">
          <div
            className="bg-primary-500 h-2 rounded-full transition-all"
            style={{ width: `${estimation.codebase_support}%` }}
          />
        </div>
        <p className="text-xs text-surface-500 mt-1">
          Percentage of patterns that already exist in codebase
        </p>
      </div>

      {/* Sprints Estimate */}
      {sprints > 0 && (
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-surface-300 mb-1">
            <TrendingUp className="w-4 h-4" />
            <span>Sprint Estimate</span>
          </div>
          <div className="text-lg font-semibold text-white">
            ~{sprints} sprint{sprints !== 1 ? 's' : ''} ({estimation.total_days.likely} days)
          </div>
        </div>
      )}
    </motion.div>
  )
}
