import { useState } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, Loader2, Shield, Eye, FileCheck, Code, Network, ExternalLink } from 'lucide-react'

interface RiskPrediction {
  predicted_findings: Record<string, number>
  predicted_severities: Record<string, number>
  estimated_review_time: string
  suggested_reviewers: string[]
  similar_reviews: Array<{ review_id: string; title: string; findings_count: number; similarity: number }>
  confidence: number
  risk_level: string
}

interface RiskPreviewProps {
  onDescriptionChange?: (desc: string) => void
}

const RISK_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10 border-red-500/30',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  low: 'text-green-400 bg-green-500/10 border-green-500/30',
  unknown: 'text-surface-400 bg-surface-800 border-surface-700',
}

const DIM_ICONS: Record<string, typeof Shield> = {
  security: Shield,
  privacy: Eye,
  compliance: FileCheck,
  engineering: Code,
  architecture: Network,
}

export default function RiskPreview({ onDescriptionChange }: RiskPreviewProps) {
  const [description, setDescription] = useState('')
  const [prediction, setPrediction] = useState<RiskPrediction | null>(null)
  const [loading, setLoading] = useState(false)

  const predict = async () => {
    if (!description.trim()) return
    setLoading(true)
    try {
      const res = await fetch('/api/predict-risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: description.trim() }),
      })
      if (res.ok) {
        setPrediction(await res.json())
      }
    } catch {}
    setLoading(false)
  }

  return (
    <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-4 space-y-3">
      <h4 className="text-sm font-semibold text-white flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-primary-400" />
        Risk Preview
      </h4>
      <p className="text-xs text-surface-400">Describe your feature to predict its risk profile.</p>

      <div className="flex gap-2">
        <input
          value={description}
          onChange={e => { setDescription(e.target.value); onDescriptionChange?.(e.target.value) }}
          onKeyDown={e => e.key === 'Enter' && predict()}
          placeholder="e.g., Add user preferences API with PII storage..."
          className="flex-1 bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs text-white placeholder-surface-500 focus:outline-none focus:border-primary-500"
        />
        <button
          onClick={predict}
          disabled={!description.trim() || loading}
          className="px-3 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 disabled:opacity-40 text-white text-xs transition-colors"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Predict'}
        </button>
      </div>

      {prediction && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          {/* Risk level */}
          <div className="flex items-center justify-between">
            <span className={`text-xs px-2 py-1 rounded-full border font-medium ${RISK_COLORS[prediction.risk_level] || RISK_COLORS.unknown}`}>
              {prediction.risk_level.toUpperCase()} risk
            </span>
            <span className="text-[10px] text-surface-500">
              {Math.round(prediction.confidence * 100)}% confidence
            </span>
          </div>

          {/* Predicted findings by dimension */}
          <div className="grid grid-cols-5 gap-1.5">
            {Object.entries(prediction.predicted_findings).map(([dim, count]) => {
              const Icon = DIM_ICONS[dim] || Shield
              return (
                <div key={dim} className="text-center p-2 rounded-lg bg-surface-800 border border-surface-700">
                  <Icon className="w-3.5 h-3.5 text-surface-400 mx-auto mb-1" />
                  <p className="text-sm font-bold text-white">{count}</p>
                  <p className="text-[9px] text-surface-500 capitalize">{dim}</p>
                </div>
              )
            })}
          </div>

          {/* Suggested reviewers */}
          {prediction.suggested_reviewers.length > 0 && (
            <div>
              <span className="text-[10px] text-surface-500">Suggested reviewers:</span>
              <div className="flex gap-1 mt-1">
                {prediction.suggested_reviewers.map(team => (
                  <span key={team} className="text-[10px] px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-400 border border-primary-500/20 capitalize">
                    {team}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Similar reviews */}
          {prediction.similar_reviews.length > 0 && (
            <div>
              <span className="text-[10px] text-surface-500">Similar past reviews:</span>
              <div className="space-y-1 mt-1">
                {prediction.similar_reviews.slice(0, 3).map(r => (
                  <a
                    key={r.review_id}
                    href={`/review/${r.review_id}`}
                    className="flex items-center justify-between px-2 py-1.5 rounded bg-surface-800 text-xs hover:bg-surface-700 transition-colors"
                  >
                    <span className="text-surface-300 truncate">{r.title || r.review_id}</span>
                    <span className="text-surface-500 flex items-center gap-1">
                      {r.findings_count} findings
                      <ExternalLink className="w-2.5 h-2.5" />
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}

          <p className="text-[10px] text-surface-500">Est. review time: {prediction.estimated_review_time}</p>
        </motion.div>
      )}
    </div>
  )
}
