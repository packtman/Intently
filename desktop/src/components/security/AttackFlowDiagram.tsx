import { motion } from 'framer-motion'
import { Activity, ArrowRight, AlertTriangle, Code2 } from 'lucide-react'
import type { AttackFlowStep } from '../../types'

interface AttackFlowDiagramProps {
  diagram?: string
  steps?: AttackFlowStep[]
  className?: string
}

export function AttackFlowDiagram({ diagram, steps, className = '' }: AttackFlowDiagramProps) {
  const hasContent = diagram || (steps && steps.length > 0)
  
  if (!hasContent) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl bg-void-900/70 border border-red-500/30 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-red-500/10 border-b border-red-500/20">
        <Activity className="w-4 h-4 text-red-400" />
        <span className="text-sm font-medium text-red-400">Attack Flow</span>
      </div>

      <div className="p-4 space-y-4">
        {/* ASCII Diagram */}
        {diagram && (
          <div className="p-3 rounded-lg bg-void-950 border border-void-700 overflow-x-auto">
            <pre className="text-xs text-void-300 font-mono whitespace-pre leading-relaxed">
              {diagram}
            </pre>
          </div>
        )}

        {/* Step-by-Step Flow */}
        {steps && steps.length > 0 && (
          <div className="space-y-3">
            {steps.map((step, index) => (
              <motion.div
                key={step.step || index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="relative"
              >
                {/* Connector Line */}
                {index < steps.length - 1 && (
                  <div className="absolute left-5 top-12 bottom-0 w-px bg-gradient-to-b from-red-500/50 to-red-500/10" />
                )}

                <div className="flex items-start gap-3">
                  {/* Step Number */}
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center">
                    <span className="text-sm font-bold text-red-400">{step.step || index + 1}</span>
                  </div>

                  {/* Step Content */}
                  <div className="flex-1 p-3 rounded-xl bg-void-800/50 border border-void-700 space-y-2">
                    <div className="flex items-center gap-2">
                      <ArrowRight className="w-3 h-3 text-red-400" />
                      <span className="text-white font-medium text-sm">{step.action}</span>
                    </div>

                    {step.system_response && (
                      <div className="pl-5 text-sm text-void-400">
                        <span className="text-void-500">System:</span> {step.system_response}
                      </div>
                    )}

                    {step.exploited_weakness && (
                      <div className="flex items-start gap-2 pl-5">
                        <AlertTriangle className="w-3 h-3 text-ember-400 mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-ember-300">{step.exploited_weakness}</span>
                      </div>
                    )}

                    {step.code_location && (
                      <div className="flex items-center gap-2 pl-5">
                        <Code2 className="w-3 h-3 text-neon-400" />
                        <code className="text-xs text-neon-300 bg-neon-500/10 px-2 py-0.5 rounded">
                          {step.code_location}
                        </code>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
