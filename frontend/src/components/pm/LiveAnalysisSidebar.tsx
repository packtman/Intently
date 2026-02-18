import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Activity, Shield, Eye, FileCheck, Code, Network, AlertTriangle, CheckCircle } from 'lucide-react'

interface LiveAnalysisResult {
  quality_score: { score: number; grade: string; gaps: string[] }
  finding_counts: Record<string, number>
  total_findings: number
  severity_breakdown: Record<string, number>
  top_issues: Array<{ title: string; severity: string; dimension: string }>
}

interface LiveAnalysisSidebarProps {
  prdContent: string
  reviewId?: string
}

const DIMENSION_ICONS: Record<string, typeof Shield> = {
  security: Shield,
  privacy: Eye,
  compliance: FileCheck,
  engineering: Code,
  architecture: Network,
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-green-400',
  info: 'text-surface-400',
}

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-400 bg-green-500/10 border-green-500/30',
  B: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  C: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  D: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  F: 'text-red-400 bg-red-500/10 border-red-500/30',
}

export default function LiveAnalysisSidebar({ prdContent, reviewId }: LiveAnalysisSidebarProps) {
  const [result, setResult] = useState<LiveAnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!prdContent || prdContent.length < 20) {
      setResult(null)
      return
    }

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      runAnalysis()
    }, 2000)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [prdContent])

  const runAnalysis = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/reviews/live-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prd_content: prdContent,
          review_id: reviewId || null,
        }),
      })
      if (res.ok) {
        setResult(await res.json())
      }
    } catch {}
    setLoading(false)
  }

  if (!result && !loading) return null

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-surface-800/50 border border-surface-700 rounded-xl p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary-400" />
          Live Analysis
        </h4>
        {loading && (
          <div className="w-3 h-3 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {result && (
        <>
          {/* Quality Score */}
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl border-2 flex items-center justify-center text-lg font-bold ${
              GRADE_COLORS[result.quality_score.grade] || GRADE_COLORS.C
            }`}>
              {result.quality_score.grade}
            </div>
            <div>
              <p className="text-sm font-medium text-white">Quality: {result.quality_score.score}/100</p>
              <p className="text-xs text-surface-400">{result.total_findings} potential issues</p>
            </div>
          </div>

          {/* Finding counts by dimension */}
          <div className="space-y-1.5">
            {Object.entries(result.finding_counts).map(([dim, count]) => {
              const Icon = DIMENSION_ICONS[dim] || Shield
              return (
                <div key={dim} className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-surface-800">
                  <div className="flex items-center gap-2">
                    <Icon className="w-3.5 h-3.5 text-surface-400" />
                    <span className="text-xs text-surface-300 capitalize">{dim}</span>
                  </div>
                  <span className={`text-xs font-medium ${count > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                    {count > 0 ? count : <CheckCircle className="w-3.5 h-3.5 inline" />}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Top issues */}
          {result.top_issues.length > 0 && (
            <div>
              <p className="text-xs text-surface-500 mb-1.5">Top Issues</p>
              <div className="space-y-1">
                {result.top_issues.map((issue, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <AlertTriangle className={`w-3 h-3 mt-0.5 flex-shrink-0 ${SEVERITY_COLORS[issue.severity] || 'text-surface-400'}`} />
                    <span className="text-surface-300 line-clamp-2">{issue.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gaps */}
          {result.quality_score.gaps.length > 0 && (
            <div>
              <p className="text-xs text-surface-500 mb-1.5">Missing Sections</p>
              <div className="flex flex-wrap gap-1">
                {result.quality_score.gaps.slice(0, 4).map((gap, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                    {gap}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </motion.div>
  )
}
