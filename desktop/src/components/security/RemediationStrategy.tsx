import { motion, AnimatePresence } from 'framer-motion'
import {
  Wrench,
  CheckCircle2,
  Clock,
  User,
  FileCode2,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  RotateCcw,
  TestTube,
  AlertCircle,
} from 'lucide-react'
import { useState } from 'react'
import type { RemediationStrategy as RemediationStrategyType } from '../../types'

interface RemediationStrategyProps {
  remediation: RemediationStrategyType
  className?: string
}

export function RemediationStrategy({ remediation, className = '' }: RemediationStrategyProps) {
  const [showSteps, setShowSteps] = useState(false)
  const [showAlternatives, setShowAlternatives] = useState(false)
  const [showVerification, setShowVerification] = useState(false)

  const priorityColors: Record<string, string> = {
    'Must Have': 'bg-red-500/20 text-red-400 border-red-500/30',
    'Should Have': 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    'Nice to Have': 'bg-green-500/20 text-green-400 border-green-500/30',
  }

  const effortColors: Record<string, string> = {
    Small: 'bg-green-500/20 text-green-400',
    Medium: 'bg-yellow-500/20 text-yellow-400',
    Large: 'bg-ember-500/20 text-ember-400',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl bg-gradient-to-br from-green-500/5 to-neon-500/5 border border-green-500/30 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-green-500/10 border-b border-green-500/20">
        <Wrench className="w-4 h-4 text-green-400" />
        <span className="text-sm font-medium text-green-400">Remediation Strategy</span>
      </div>

      <div className="p-4 space-y-4">
        {/* Summary */}
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-white font-medium">{remediation.summary}</p>
          </div>
        </div>

        {/* Metadata Badges */}
        <div className="flex flex-wrap items-center gap-2">
          {remediation.priority && (
            <span className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${priorityColors[remediation.priority] || 'bg-void-700 text-void-300'}`}>
              {remediation.priority}
            </span>
          )}
          {remediation.effort && (
            <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${effortColors[remediation.effort] || 'bg-void-700 text-void-300'}`}>
              <Clock className="w-3 h-3 inline mr-1" />
              {remediation.effort} Effort
            </span>
          )}
          {remediation.owner && (
            <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-void-700 text-void-300">
              <User className="w-3 h-3 inline mr-1" />
              {remediation.owner}
            </span>
          )}
        </div>

        {/* Detailed Strategy */}
        {remediation.detailed_strategy && (
          <div className="p-3 rounded-lg bg-void-800/50 border border-void-700">
            <p className="text-sm text-void-300 leading-relaxed whitespace-pre-wrap">
              {remediation.detailed_strategy}
            </p>
          </div>
        )}

        {/* Implementation Steps */}
        {remediation.implementation_steps && remediation.implementation_steps.length > 0 && (
          <div className="rounded-lg bg-void-800/30 border border-void-700 overflow-hidden">
            <button
              onClick={() => setShowSteps(!showSteps)}
              className="w-full flex items-center justify-between p-3 hover:bg-void-800/50 transition-colors"
            >
              <span className="text-sm font-medium text-white flex items-center gap-2">
                <FileCode2 className="w-4 h-4 text-neon-400" />
                Implementation Steps ({remediation.implementation_steps.length})
              </span>
              {showSteps ? (
                <ChevronDown className="w-4 h-4 text-void-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-void-400" />
              )}
            </button>

            <AnimatePresence>
              {showSteps && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-void-700"
                >
                  <div className="p-3 space-y-3">
                    {remediation.implementation_steps.map((step, index) => (
                      <div
                        key={step.step || index}
                        className="flex items-start gap-3 p-3 rounded-lg bg-void-900/50"
                      >
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-neon-500/20 border border-neon-500/40 flex items-center justify-center">
                          <span className="text-xs font-bold text-neon-400">{step.step || index + 1}</span>
                        </div>
                        <div className="flex-1 space-y-2">
                          <p className="text-sm text-white font-medium">{step.action}</p>
                          {step.code_changes && (
                            <p className="text-xs text-void-400">
                              <span className="text-neon-400">Code:</span> {step.code_changes}
                            </p>
                          )}
                          {step.files_to_modify && step.files_to_modify.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {step.files_to_modify.map((file) => (
                                <code key={file} className="text-xs text-cyan-300 bg-cyan-500/10 px-1.5 py-0.5 rounded">
                                  {file}
                                </code>
                              ))}
                            </div>
                          )}
                          {step.estimated_effort && (
                            <span className="inline-flex items-center gap-1 text-xs text-void-400">
                              <Clock className="w-3 h-3" />
                              {step.estimated_effort}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Code Example */}
        {remediation.code_example && (
          <div className="rounded-lg bg-void-950 border border-void-700 overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 bg-void-900/50 border-b border-void-700">
              <Lightbulb className="w-3 h-3 text-green-400" />
              <span className="text-xs font-medium text-green-400">Example Secure Implementation</span>
            </div>
            <pre className="p-3 text-xs text-green-300 font-mono overflow-x-auto whitespace-pre leading-relaxed">
              {remediation.code_example}
            </pre>
          </div>
        )}

        {/* Alternative Approaches */}
        {remediation.alternative_approaches && remediation.alternative_approaches.length > 0 && (
          <div className="rounded-lg bg-void-800/30 border border-void-700 overflow-hidden">
            <button
              onClick={() => setShowAlternatives(!showAlternatives)}
              className="w-full flex items-center justify-between p-3 hover:bg-void-800/50 transition-colors"
            >
              <span className="text-sm font-medium text-white flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-400" />
                Alternative Approaches ({remediation.alternative_approaches.length})
              </span>
              {showAlternatives ? (
                <ChevronDown className="w-4 h-4 text-void-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-void-400" />
              )}
            </button>

            <AnimatePresence>
              {showAlternatives && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-void-700"
                >
                  <div className="p-3 space-y-3">
                    {remediation.alternative_approaches.map((alt, index) => (
                      <div key={index} className="p-3 rounded-lg bg-void-900/50 space-y-2">
                        <p className="text-sm text-white font-medium">{alt.approach}</p>
                        {alt.pros && alt.pros.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {alt.pros.map((pro, i) => (
                              <span key={i} className="text-xs text-green-300 bg-green-500/10 px-2 py-0.5 rounded">
                                + {pro}
                              </span>
                            ))}
                          </div>
                        )}
                        {alt.cons && alt.cons.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {alt.cons.map((con, i) => (
                              <span key={i} className="text-xs text-red-300 bg-red-500/10 px-2 py-0.5 rounded">
                                - {con}
                              </span>
                            ))}
                          </div>
                        )}
                        {alt.when_to_use && (
                          <p className="text-xs text-void-400 italic">{alt.when_to_use}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Verification */}
        {remediation.verification && Object.keys(remediation.verification).length > 0 && (
          <div className="rounded-lg bg-void-800/30 border border-void-700 overflow-hidden">
            <button
              onClick={() => setShowVerification(!showVerification)}
              className="w-full flex items-center justify-between p-3 hover:bg-void-800/50 transition-colors"
            >
              <span className="text-sm font-medium text-white flex items-center gap-2">
                <TestTube className="w-4 h-4 text-cyan-400" />
                Verification & Testing
              </span>
              {showVerification ? (
                <ChevronDown className="w-4 h-4 text-void-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-void-400" />
              )}
            </button>

            <AnimatePresence>
              {showVerification && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-void-700"
                >
                  <div className="p-3 space-y-3">
                    {remediation.verification.how_to_test && (
                      <div>
                        <p className="text-xs font-medium text-void-400 mb-1">How to Test</p>
                        <p className="text-sm text-white">{remediation.verification.how_to_test}</p>
                      </div>
                    )}
                    {remediation.verification.test_cases && remediation.verification.test_cases.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-void-400 mb-2">Test Cases</p>
                        <ul className="space-y-1">
                          {remediation.verification.test_cases.map((tc, i) => (
                            <li key={i} className="text-sm text-cyan-300 flex items-start gap-2">
                              <span className="text-cyan-400">-</span>
                              {tc}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {remediation.verification.security_tests && remediation.verification.security_tests.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-void-400 mb-2">Security Tests</p>
                        <ul className="space-y-1">
                          {remediation.verification.security_tests.map((st, i) => (
                            <li key={i} className="text-sm text-aurora-300 flex items-start gap-2">
                              <span className="text-aurora-400">-</span>
                              {st}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Dependencies */}
        {remediation.dependencies && remediation.dependencies.length > 0 && (
          <div className="p-3 rounded-lg bg-void-800/50 border border-void-700">
            <p className="text-xs font-medium text-void-400 mb-2">Dependencies (fix these first)</p>
            <div className="flex flex-wrap gap-2">
              {remediation.dependencies.map((dep, i) => (
                <span key={i} className="text-xs text-ember-300 bg-ember-500/10 px-2 py-1 rounded">
                  {dep}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Rollback Plan */}
        {remediation.rollback_plan && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <RotateCcw className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-medium text-yellow-400 mb-1">Rollback Plan</p>
              <p className="text-sm text-yellow-200">{remediation.rollback_plan}</p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
