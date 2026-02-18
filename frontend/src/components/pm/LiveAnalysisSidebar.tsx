import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { BookOpen } from 'lucide-react'

interface QualityResult {
  quality_score: { score: number; grade: string; gaps: string[] }
}

interface LiveAnalysisSidebarProps {
  prdContent: string
}

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-400 bg-green-500/10 border-green-500/30',
  B: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  C: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  D: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  F: 'text-red-400 bg-red-500/10 border-red-500/30',
}

export default function LiveAnalysisSidebar({ prdContent }: LiveAnalysisSidebarProps) {
  const [result, setResult] = useState<QualityResult | null>(null)
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
        body: JSON.stringify({ prd_content: prdContent }),
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
          <BookOpen className="w-4 h-4 text-primary-400" />
          PRD Writing Guide
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
              <p className="text-xs text-surface-400">Based on PRD structure and completeness</p>
            </div>
          </div>

          {/* Gaps */}
          {result.quality_score.gaps.length > 0 && (
            <div>
              <p className="text-xs text-surface-500 mb-1.5">Missing Sections</p>
              <div className="flex flex-wrap gap-1">
                {result.quality_score.gaps.map((gap, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                    {gap}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.quality_score.gaps.length === 0 && (
            <p className="text-xs text-green-400">All key sections covered</p>
          )}
        </>
      )}
    </motion.div>
  )
}
