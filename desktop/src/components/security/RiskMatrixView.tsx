import { motion } from 'framer-motion'
import { Grid3X3, AlertTriangle, TrendingUp, Wrench } from 'lucide-react'
import type { RiskMatrixEntry, PrioritizedMitigation } from '../../types'

interface RiskMatrixViewProps {
  matrix: RiskMatrixEntry[]
  priority1Mitigations?: PrioritizedMitigation[]
  priority2Mitigations?: PrioritizedMitigation[]
  priority3Mitigations?: PrioritizedMitigation[]
  className?: string
}

export function RiskMatrixView({
  matrix,
  priority1Mitigations,
  priority2Mitigations,
  priority3Mitigations,
  className = '',
}: RiskMatrixViewProps) {
  if (!matrix || matrix.length === 0) return null

  const severityColors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
    HIGH: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
  }

  const likelihoodColors: Record<string, string> = {
    HIGH: 'text-red-400',
    MEDIUM: 'text-yellow-400',
    LOW: 'text-green-400',
    high: 'text-red-400',
    medium: 'text-yellow-400',
    low: 'text-green-400',
  }

  const hasMitigations =
    (priority1Mitigations && priority1Mitigations.length > 0) ||
    (priority2Mitigations && priority2Mitigations.length > 0) ||
    (priority3Mitigations && priority3Mitigations.length > 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl bg-gradient-to-br from-purple-500/5 to-neon-500/5 border border-purple-500/30 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 bg-purple-500/10 border-b border-purple-500/20">
        <Grid3X3 className="w-5 h-5 text-purple-400" />
        <div>
          <h3 className="font-display font-semibold text-white">Risk Assessment Matrix</h3>
          <p className="text-xs text-purple-300/70">{matrix.length} threats identified and prioritized</p>
        </div>
      </div>

      {/* Risk Matrix Table */}
      <div className="p-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-void-400 border-b border-void-700">
              <th className="text-left py-3 px-3 font-medium">ID</th>
              <th className="text-left py-3 px-3 font-medium">Attack</th>
              <th className="text-left py-3 px-3 font-medium">Exploits</th>
              <th className="text-left py-3 px-3 font-medium">Impact</th>
              <th className="text-center py-3 px-3 font-medium">Likelihood</th>
              <th className="text-center py-3 px-3 font-medium">Severity</th>
              {matrix.some((m) => m.cvss_estimate) && (
                <th className="text-center py-3 px-3 font-medium">CVSS</th>
              )}
            </tr>
          </thead>
          <tbody>
            {matrix.map((entry, index) => (
              <motion.tr
                key={entry.threat_id || index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="border-b border-void-800 hover:bg-void-800/30 transition-colors"
              >
                <td className="py-3 px-3">
                  <span className="font-mono text-neon-400 font-medium">{entry.threat_id}</span>
                </td>
                <td className="py-3 px-3">
                  <span className="text-white">{entry.attack}</span>
                </td>
                <td className="py-3 px-3">
                  <span className="text-void-300 text-xs">{entry.exploits}</span>
                </td>
                <td className="py-3 px-3">
                  <span className="text-void-300 text-xs max-w-[200px] truncate block">{entry.impact}</span>
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`font-medium ${likelihoodColors[entry.likelihood] || 'text-void-300'}`}>
                    {entry.likelihood}
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <span
                    className={`px-2 py-1 rounded-lg text-xs font-medium border ${severityColors[entry.severity] || 'bg-void-700 text-void-300'}`}
                  >
                    {entry.severity?.toUpperCase()}
                  </span>
                </td>
                {matrix.some((m) => m.cvss_estimate) && (
                  <td className="py-3 px-3 text-center">
                    {entry.cvss_estimate ? (
                      <CvssScore score={entry.cvss_estimate} />
                    ) : (
                      <span className="text-void-500">-</span>
                    )}
                  </td>
                )}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Prioritized Mitigations */}
      {hasMitigations && (
        <div className="border-t border-void-700 p-4 space-y-4">
          <div className="flex items-center gap-2">
            <Wrench className="w-4 h-4 text-green-400" />
            <h4 className="font-medium text-white">Prioritized Mitigations</h4>
          </div>

          {/* Priority 1 - Must Have */}
          {priority1Mitigations && priority1Mitigations.length > 0 && (
            <MitigationSection
              title="Priority 1: Must Have Before Launch"
              mitigations={priority1Mitigations}
              color="red"
              icon={AlertTriangle}
            />
          )}

          {/* Priority 2 - Should Have */}
          {priority2Mitigations && priority2Mitigations.length > 0 && (
            <MitigationSection
              title="Priority 2: Should Have"
              mitigations={priority2Mitigations}
              color="yellow"
              icon={TrendingUp}
            />
          )}

          {/* Priority 3 - Nice to Have */}
          {priority3Mitigations && priority3Mitigations.length > 0 && (
            <MitigationSection
              title="Priority 3: Nice to Have"
              mitigations={priority3Mitigations}
              color="green"
              icon={Wrench}
            />
          )}
        </div>
      )}
    </motion.div>
  )
}

function CvssScore({ score }: { score: number }) {
  const getColor = () => {
    if (score >= 9.0) return 'text-red-400 bg-red-500/20'
    if (score >= 7.0) return 'text-ember-400 bg-ember-500/20'
    if (score >= 4.0) return 'text-yellow-400 bg-yellow-500/20'
    return 'text-green-400 bg-green-500/20'
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${getColor()}`}>
      {score.toFixed(1)}
    </span>
  )
}

function MitigationSection({
  title,
  mitigations,
  color,
  icon: Icon,
}: {
  title: string
  mitigations: PrioritizedMitigation[]
  color: 'red' | 'yellow' | 'green'
  icon: typeof AlertTriangle
}) {
  const colorClasses: Record<string, string> = {
    red: 'bg-red-500/10 border-red-500/30 text-red-400',
    yellow: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
  }

  return (
    <div className={`rounded-xl border ${colorClasses[color]} p-4`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4" />
        <span className="text-sm font-medium">{title}</span>
      </div>
      <div className="space-y-3">
        {mitigations.map((m, index) => (
          <div key={index} className="bg-void-900/50 rounded-lg p-3 space-y-2">
            <p className="text-sm text-white font-medium">{m.mitigation}</p>
            {m.addresses && m.addresses.length > 0 && (
              <div className="flex flex-wrap gap-1">
                <span className="text-xs text-void-500">Addresses:</span>
                {m.addresses.map((id) => (
                  <code key={id} className="text-xs text-neon-300 bg-neon-500/10 px-1.5 py-0.5 rounded">
                    {id}
                  </code>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-3 text-xs text-void-400">
              {m.owner && (
                <span>
                  Owner: <span className="text-void-300">{m.owner}</span>
                </span>
              )}
              {m.effort && (
                <span>
                  Effort: <span className="text-void-300">{m.effort}</span>
                </span>
              )}
              {m.timeline && (
                <span>
                  Timeline: <span className="text-void-300">{m.timeline}</span>
                </span>
              )}
            </div>
            {m.detailed_implementation && (
              <p className="text-xs text-void-400 leading-relaxed">{m.detailed_implementation}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
