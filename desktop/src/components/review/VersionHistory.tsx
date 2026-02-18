import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { History, GitCommit, ArrowRight, Plus, Diff } from 'lucide-react'

interface VersionInfo {
  id: string
  review_id: string
  version_number: number
  author: string
  change_summary: string
  quality_score: number | null
  finding_count: number | null
  content_length: number
  created_at: string
}

interface VersionHistoryProps {
  reviewId: string
}

export default function VersionHistory({ reviewId }: VersionHistoryProps) {
  const [versions, setVersions] = useState<VersionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [diffing, setDiffing] = useState(false)
  const [selectedVersions, setSelectedVersions] = useState<[number, number] | null>(null)
  const [diffResult, setDiffResult] = useState<any>(null)
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000')

  useEffect(() => {
    if (window.electronAPI?.getBackendUrl) {
      window.electronAPI.getBackendUrl().then(setBaseUrl)
    }
  }, [])

  useEffect(() => {
    fetchVersions()
  }, [reviewId, baseUrl])

  const fetchVersions = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/reviews/${reviewId}/versions`)
      if (res.ok) {
        setVersions(await res.json())
      }
    } catch {}
    setLoading(false)
  }

  const saveVersion = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/reviews/${reviewId}/versions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author: 'current-user', change_summary: '' }),
      })
      if (res.ok) {
        fetchVersions()
      }
    } catch {}
  }

  const compareTwoVersions = async (v1: number, v2: number) => {
    setDiffing(true)
    setSelectedVersions([v1, v2])
    try {
      const res = await fetch(`${baseUrl}/api/reviews/${reviewId}/versions/${v1}/${v2}/diff`)
      if (res.ok) {
        setDiffResult(await res.json())
      }
    } catch {}
    setDiffing(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <History className="w-4 h-4 text-primary-400" />
          Version History
        </h4>
        <button
          onClick={saveVersion}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 text-xs hover:bg-primary-500/30 transition-colors"
        >
          <Plus className="w-3 h-3" />
          Save Version
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full" />
        </div>
      ) : versions.length === 0 ? (
        <p className="text-xs text-surface-500 text-center py-4">
          No versions saved yet. Click "Save Version" to create a snapshot.
        </p>
      ) : (
        <div className="space-y-2">
          {versions.map((version, i) => (
            <motion.div
              key={version.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-surface-800 border border-surface-700 group"
            >
              <div className="flex-shrink-0">
                <GitCommit className="w-4 h-4 text-primary-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-white">v{version.version_number}</span>
                  {version.quality_score !== null && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400">
                      Score: {version.quality_score}
                    </span>
                  )}
                  {version.finding_count !== null && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400">
                      {version.finding_count} findings
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-surface-500 truncate">
                  {version.change_summary || 'No description'} · {new Date(version.created_at).toLocaleString()}
                </p>
              </div>
              {i > 0 && (
                <button
                  onClick={() => compareTwoVersions(versions[i - 1].version_number, version.version_number)}
                  className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 rounded bg-surface-700 text-xs text-surface-300 hover:bg-surface-600"
                >
                  <Diff className="w-3 h-3" />
                </button>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Diff result */}
      {diffResult && selectedVersions && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-800 border border-surface-700 rounded-xl p-4 space-y-3"
        >
          <div className="flex items-center gap-2 text-xs text-surface-400">
            <span>v{selectedVersions[0]}</span>
            <ArrowRight className="w-3 h-3" />
            <span>v{selectedVersions[1]}</span>
            <button
              onClick={() => { setDiffResult(null); setSelectedVersions(null) }}
              className="ml-auto text-surface-500 hover:text-white"
            >
              Close
            </button>
          </div>

          {/* Analysis diff */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2 rounded-lg bg-surface-900">
              <span className="text-[10px] text-surface-500 block mb-1">Findings</span>
              <span className={`text-sm font-medium ${
                diffResult.analysis_diff.finding_count.delta > 0 ? 'text-red-400' :
                diffResult.analysis_diff.finding_count.delta < 0 ? 'text-green-400' :
                'text-surface-300'
              }`}>
                {diffResult.analysis_diff.finding_count.delta > 0 ? '+' : ''}
                {diffResult.analysis_diff.finding_count.delta}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-surface-900">
              <span className="text-[10px] text-surface-500 block mb-1">Quality</span>
              <span className={`text-sm font-medium ${
                (diffResult.analysis_diff.quality_score.delta || 0) > 0 ? 'text-green-400' :
                (diffResult.analysis_diff.quality_score.delta || 0) < 0 ? 'text-red-400' :
                'text-surface-300'
              }`}>
                {(diffResult.analysis_diff.quality_score.delta || 0) > 0 ? '+' : ''}
                {diffResult.analysis_diff.quality_score.delta ?? 'N/A'}
              </span>
            </div>
          </div>

          {/* Text diff stats */}
          <div className="text-xs text-surface-400">
            <span className="text-green-400">+{diffResult.text_diff.stats.lines_added}</span>
            {' / '}
            <span className="text-red-400">-{diffResult.text_diff.stats.lines_removed}</span>
            {' / '}
            <span className="text-yellow-400">~{diffResult.text_diff.stats.lines_modified}</span>
            {' lines'}
          </div>
        </motion.div>
      )}
    </div>
  )
}
