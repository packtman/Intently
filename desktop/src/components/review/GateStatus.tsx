import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, ShieldAlert, ShieldQuestion, Lock, Unlock } from 'lucide-react'

interface GateResult {
  name: string
  condition: string
  blocking: boolean
  passed: boolean
  reason: string
  details: Record<string, any>
}

interface GateStatusProps {
  reviewId: string
}

export default function GateStatus({ reviewId }: GateStatusProps) {
  const [gates, setGates] = useState<GateResult[]>([])
  const [allPassed, setAllPassed] = useState(true)
  const [blockingFailures, setBlockingFailures] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000')

  useEffect(() => {
    if (window.electronAPI?.getBackendUrl) {
      window.electronAPI.getBackendUrl().then(setBaseUrl)
    }
  }, [])

  useEffect(() => {
    fetchGates()
  }, [reviewId, baseUrl])

  const fetchGates = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/reviews/${reviewId}/gates`)
      if (!res.ok) {
        if (res.status === 403) return // Feature not enabled, silently skip
        throw new Error(`HTTP ${res.status}`)
      }
      const data = await res.json()
      setGates(data.gates || [])
      setAllPassed(data.all_passed)
      setBlockingFailures(data.blocking_failures || 0)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading || error || gates.length === 0) return null

  return (
    <div className="bg-surface-800/50 border border-surface-700 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          {allPassed ? (
            <ShieldCheck className="w-4 h-4 text-green-400" />
          ) : blockingFailures > 0 ? (
            <ShieldAlert className="w-4 h-4 text-red-400" />
          ) : (
            <ShieldQuestion className="w-4 h-4 text-yellow-400" />
          )}
          Approval Gates
        </h4>
        <span className={`text-xs px-2 py-0.5 rounded-full border ${
          allPassed
            ? 'text-green-400 bg-green-500/10 border-green-500/30'
            : blockingFailures > 0
              ? 'text-red-400 bg-red-500/10 border-red-500/30'
              : 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
        }`}>
          {allPassed ? 'All Passed' : `${blockingFailures} blocked`}
        </span>
      </div>

      <div className="space-y-1.5">
        {gates.map((gate, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`flex items-center justify-between px-3 py-2 rounded-lg border ${
              gate.passed
                ? 'bg-green-500/5 border-green-500/20'
                : gate.blocking
                  ? 'bg-red-500/5 border-red-500/20'
                  : 'bg-yellow-500/5 border-yellow-500/20'
            }`}
          >
            <div className="flex items-center gap-2">
              {gate.passed ? (
                <Unlock className="w-3.5 h-3.5 text-green-400" />
              ) : (
                <Lock className={`w-3.5 h-3.5 ${gate.blocking ? 'text-red-400' : 'text-yellow-400'}`} />
              )}
              <div>
                <span className="text-xs text-white">{gate.name}</span>
                <p className="text-[10px] text-surface-500">{gate.reason}</p>
              </div>
            </div>
            {!gate.passed && gate.blocking && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                blocks
              </span>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  )
}
