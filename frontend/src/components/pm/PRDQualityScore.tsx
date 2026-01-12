/**
 * PRD Quality Score Component
 * 
 * Displays PRD readiness score, grade, and gaps
 */

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { TrendingUp, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../../services/api'
import type { PRDQualityScore as PRDQualityScoreType } from '../../types'

interface PRDQualityScoreProps {
  reviewId: string
}

export function PRDQualityScore({ reviewId }: PRDQualityScoreProps) {
  const { data: quality, isLoading } = useQuery({
    queryKey: ['prd-quality', reviewId],
    queryFn: () => api.getPRDQuality(reviewId),
    enabled: !!reviewId,
  })

  if (isLoading) {
    return (
      <div className="bg-surface-900/50 rounded-xl border border-surface-800 p-6">
        <div className="text-surface-400">Loading quality score...</div>
      </div>
    )
  }

  if (!quality) {
    return null
  }

  const gradeColors: Record<string, string> = {
    A: 'text-green-400',
    B: 'text-blue-400',
    C: 'text-amber-400',
    D: 'text-orange-400',
    F: 'text-red-400',
  }

  const gradeBgColors: Record<string, string> = {
    A: 'bg-green-500/20 border-green-500/50',
    B: 'bg-blue-500/20 border-blue-500/50',
    C: 'bg-amber-500/20 border-amber-500/50',
    D: 'bg-orange-500/20 border-orange-500/50',
    F: 'bg-red-500/20 border-red-500/50',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-900/50 rounded-xl border border-surface-800 p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">PRD Quality Score</h3>
        <div className={`px-4 py-2 rounded-lg border ${gradeBgColors[quality.grade]}`}>
          <div className={`text-3xl font-bold ${gradeColors[quality.grade]}`}>
            {quality.grade}
          </div>
        </div>
      </div>

      {/* Score Circle */}
      <div className="flex items-center justify-center mb-6">
        <div className="relative w-32 h-32">
          <svg className="transform -rotate-90 w-32 h-32">
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-surface-800"
            />
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${(quality.score / 100) * 352} 352`}
              className={gradeColors[quality.grade]}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className={`text-2xl font-bold ${gradeColors[quality.grade]}`}>
                {quality.score}
              </div>
              <div className="text-xs text-surface-400">out of 100</div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-red-400">{quality.blockers}</div>
          <div className="text-xs text-surface-400">Blockers</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-amber-400">{quality.likely_questions}</div>
          <div className="text-xs text-surface-400">Likely</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{quality.possible_questions}</div>
          <div className="text-xs text-surface-400">Possible</div>
        </div>
      </div>

      {/* Gaps */}
      {quality.gaps.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-surface-300">
            <AlertCircle className="w-4 h-4" />
            Key Gaps
          </div>
          <ul className="space-y-1">
            {quality.gaps.map((gap, i) => (
              <li key={i} className="text-sm text-surface-400 flex items-start gap-2">
                <span className="text-surface-600 mt-1">•</span>
                <span>{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  )
}
