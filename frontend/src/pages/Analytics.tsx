import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, Shield, AlertTriangle, CheckCircle, PieChart } from 'lucide-react'

interface AnalyticsData {
  overview: {
    total_reviews: number
    completed: number
    total_findings: number
    avg_findings_per_review: number
  }
  findings_by_dimension: Record<string, number>
  findings_by_severity: Record<string, number>
  quality_trend: Array<{ review_id: string; date: string; score: number; grade: string }>
  top_finding_categories: Array<{ category: string; count: number }>
}

const DIMENSION_COLORS: Record<string, string> = {
  security: '#ef4444',
  privacy: '#a855f7',
  compliance: '#3b82f6',
  engineering: '#22c55e',
  architecture: '#f97316',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
  info: '#6b7280',
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const res = await fetch('/api/analytics')
      if (!res.ok) {
        if (res.status === 403) throw new Error('Enable FEATURE_REVIEW_ANALYTICS=true')
        throw new Error(`HTTP ${res.status}`)
      }
      setData(await res.json())
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <BarChart3 className="w-10 h-10 text-surface-600 mx-auto mb-3" />
        <p className="text-surface-400">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const maxDimCount = Math.max(...Object.values(data.findings_by_dimension), 1)
  const maxSevCount = Math.max(...Object.values(data.findings_by_severity), 1)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-display font-bold text-white">Review Analytics</h1>
        <p className="text-surface-400 mt-1">Aggregated insights across all reviews</p>
      </div>

      {/* Overview cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Reviews', value: data.overview.total_reviews, icon: Shield },
          { label: 'Completed', value: data.overview.completed, icon: CheckCircle },
          { label: 'Total Findings', value: data.overview.total_findings, icon: AlertTriangle },
          { label: 'Avg per Review', value: data.overview.avg_findings_per_review, icon: TrendingUp },
        ].map(card => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-surface-800/50 border border-surface-700 rounded-xl p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <card.icon className="w-4 h-4 text-primary-400" />
              <span className="text-xs text-surface-400">{card.label}</span>
            </div>
            <p className="text-2xl font-bold text-white">{card.value}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Findings by Dimension */}
        <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-primary-400" />
            Findings by Dimension
          </h3>
          <div className="space-y-3">
            {Object.entries(data.findings_by_dimension).map(([dim, count]) => (
              <div key={dim}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-surface-300 capitalize">{dim}</span>
                  <span className="text-surface-400">{count}</span>
                </div>
                <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(count / maxDimCount) * 100}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: DIMENSION_COLORS[dim] || '#6b7280' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Findings by Severity */}
        <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-primary-400" />
            Findings by Severity
          </h3>
          <div className="space-y-3">
            {Object.entries(data.findings_by_severity).map(([sev, count]) => (
              <div key={sev}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-surface-300 capitalize">{sev}</span>
                  <span className="text-surface-400">{count}</span>
                </div>
                <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(count / maxSevCount) * 100}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: SEVERITY_COLORS[sev] || '#6b7280' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Finding Categories */}
      {data.top_finding_categories.length > 0 && (
        <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Top Finding Categories</h3>
          <div className="grid grid-cols-2 gap-2">
            {data.top_finding_categories.map((cat, i) => (
              <div key={cat.category} className="flex items-center justify-between px-3 py-2 bg-surface-800 rounded-lg border border-surface-700">
                <span className="text-xs text-surface-300 capitalize">{cat.category.replace(/_/g, ' ')}</span>
                <span className="text-xs font-medium text-primary-400">{cat.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quality Trend */}
      {data.quality_trend.length > 0 && (
        <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary-400" />
            Quality Score Trend
          </h3>
          <div className="flex items-end gap-2 h-32">
            {data.quality_trend.map((point, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] text-surface-400">{point.grade}</span>
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${point.score}%` }}
                  transition={{ duration: 0.5, delay: i * 0.05 }}
                  className="w-full rounded-t bg-gradient-to-t from-primary-600 to-primary-400 min-h-[4px]"
                />
                <span className="text-[10px] text-surface-500">{point.score}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
