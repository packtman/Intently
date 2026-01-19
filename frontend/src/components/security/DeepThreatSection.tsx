import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Target,
  FileText,
  CheckSquare,
  TestTube,
  BookOpen,
} from 'lucide-react'
import { useState } from 'react'
import { RiskMatrixView } from './RiskMatrixView'
import type { DeepThreatModelSummary, AttackSurfaceChange } from '../../types'

interface DeepThreatSectionProps {
  threatModel: DeepThreatModelSummary
  className?: string
}

export function DeepThreatSection({ threatModel, className = '' }: DeepThreatSectionProps) {
  const [showAttackSurface, setShowAttackSurface] = useState(false)
  const [showChecklist, setShowChecklist] = useState(false)
  const [showDomainTerms, setShowDomainTerms] = useState(false)

  const riskRatingColors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
    HIGH: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`space-y-6 ${className}`}
    >
      {/* Executive Summary Card */}
      {(threatModel.executive_summary || threatModel.key_finding) && (
        <div className="card-glass rounded-2xl overflow-hidden">
          <div className="flex items-center gap-3 px-6 py-4 bg-gradient-to-r from-neon-500/10 to-purple-500/10 border-b border-neon-500/20">
            <Shield className="w-5 h-5 text-neon-400" />
            <div className="flex-1">
              <h3 className="font-display font-semibold text-white">Deep Threat Analysis</h3>
              <p className="text-xs text-void-400">Comprehensive security threat model</p>
            </div>
            {threatModel.risk_rating && (
              <span
                className={`px-3 py-1.5 rounded-xl text-sm font-semibold border ${riskRatingColors[threatModel.risk_rating] || 'bg-void-700 text-void-300'}`}
              >
                {threatModel.risk_rating} RISK
              </span>
            )}
          </div>

          <div className="p-6 space-y-4">
            {threatModel.executive_summary && (
              <div>
                <h4 className="text-sm font-medium text-void-400 mb-2">Executive Summary</h4>
                <p className="text-white leading-relaxed">{threatModel.executive_summary}</p>
              </div>
            )}

            {threatModel.key_finding && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
                <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-400 mb-1">Key Finding</p>
                  <p className="text-red-200">{threatModel.key_finding}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Architecture Flow Diagram */}
      {threatModel.current_vs_proposed_flow && (
        <div className="card-glass rounded-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-6 py-4 border-b border-void-700">
            <Target className="w-5 h-5 text-aurora-400" />
            <h3 className="font-display font-semibold text-white">Architecture Change Analysis</h3>
          </div>
          <div className="p-6">
            <div className="p-4 rounded-xl bg-void-950 border border-void-700 overflow-x-auto">
              <pre className="text-sm text-void-300 font-mono whitespace-pre leading-relaxed">
                {threatModel.current_vs_proposed_flow}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Attack Surface Expansion */}
      {threatModel.attack_surface_expansion && threatModel.attack_surface_expansion.length > 0 && (
        <div className="card-glass rounded-2xl overflow-hidden">
          <button
            onClick={() => setShowAttackSurface(!showAttackSurface)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-void-800/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-ember-400" />
              <div className="text-left">
                <h3 className="font-display font-semibold text-white">Attack Surface Changes</h3>
                <p className="text-xs text-void-400">
                  {threatModel.attack_surface_expansion.length} components with expanded exposure
                </p>
              </div>
            </div>
            {showAttackSurface ? (
              <ChevronDown className="w-5 h-5 text-void-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-void-400" />
            )}
          </button>

          <AnimatePresence>
            {showAttackSurface && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-void-700 overflow-hidden"
              >
                <div className="p-6 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-void-400 border-b border-void-700">
                        <th className="text-left py-3 px-3 font-medium">Component</th>
                        <th className="text-left py-3 px-3 font-medium">Current Exposure</th>
                        <th className="text-left py-3 px-3 font-medium">Proposed Exposure</th>
                        <th className="text-left py-3 px-3 font-medium">Change Impact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {threatModel.attack_surface_expansion.map((change, index) => (
                        <AttackSurfaceRow key={index} change={change} index={index} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Risk Matrix */}
      {threatModel.risk_matrix && threatModel.risk_matrix.length > 0 && (
        <RiskMatrixView
          matrix={threatModel.risk_matrix}
          priority1Mitigations={threatModel.priority_1_mitigations}
          priority2Mitigations={threatModel.priority_2_mitigations}
          priority3Mitigations={threatModel.priority_3_mitigations}
        />
      )}

      {/* Implementation Checklist */}
      {((threatModel.pre_launch_checklist && threatModel.pre_launch_checklist.length > 0) ||
        (threatModel.testing_requirements && threatModel.testing_requirements.length > 0)) && (
        <div className="card-glass rounded-2xl overflow-hidden">
          <button
            onClick={() => setShowChecklist(!showChecklist)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-void-800/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <CheckSquare className="w-5 h-5 text-green-400" />
              <div className="text-left">
                <h3 className="font-display font-semibold text-white">Implementation Checklist</h3>
                <p className="text-xs text-void-400">
                  {(threatModel.pre_launch_checklist?.length || 0) +
                    (threatModel.testing_requirements?.length || 0)}{' '}
                  items
                </p>
              </div>
            </div>
            {showChecklist ? (
              <ChevronDown className="w-5 h-5 text-void-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-void-400" />
            )}
          </button>

          <AnimatePresence>
            {showChecklist && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-void-700 overflow-hidden"
              >
                <div className="p-6 space-y-6">
                  {threatModel.pre_launch_checklist && threatModel.pre_launch_checklist.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-red-400 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        Pre-Launch Security Requirements
                      </h4>
                      <ul className="space-y-2">
                        {threatModel.pre_launch_checklist.map((item, i) => (
                          <li key={i} className="flex items-start gap-3 text-sm">
                            <span className="text-red-400 mt-0.5">-</span>
                            <span className="text-white">{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {threatModel.testing_requirements && threatModel.testing_requirements.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-cyan-400 mb-3 flex items-center gap-2">
                        <TestTube className="w-4 h-4" />
                        Testing Requirements
                      </h4>
                      <ul className="space-y-2">
                        {threatModel.testing_requirements.map((item, i) => (
                          <li key={i} className="flex items-start gap-3 text-sm">
                            <span className="text-cyan-400 mt-0.5">-</span>
                            <span className="text-white">{item}</span>
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

      {/* Domain Terms & PRD Quotes */}
      {((threatModel.domain_terms_identified && threatModel.domain_terms_identified.length > 0) ||
        (threatModel.prd_quotes_analyzed && threatModel.prd_quotes_analyzed.length > 0)) && (
        <div className="card-glass rounded-2xl overflow-hidden">
          <button
            onClick={() => setShowDomainTerms(!showDomainTerms)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-void-800/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <BookOpen className="w-5 h-5 text-purple-400" />
              <div className="text-left">
                <h3 className="font-display font-semibold text-white">Analysis Context</h3>
                <p className="text-xs text-void-400">
                  Domain terms and PRD quotes analyzed
                </p>
              </div>
            </div>
            {showDomainTerms ? (
              <ChevronDown className="w-5 h-5 text-void-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-void-400" />
            )}
          </button>

          <AnimatePresence>
            {showDomainTerms && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-void-700 overflow-hidden"
              >
                <div className="p-6 space-y-6">
                  {threatModel.domain_terms_identified && threatModel.domain_terms_identified.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-purple-400 mb-3">Domain Terms Identified</h4>
                      <div className="flex flex-wrap gap-2">
                        {threatModel.domain_terms_identified.map((term, i) => (
                          <code key={i} className="text-xs text-purple-300 bg-purple-500/10 px-2 py-1 rounded">
                            {term}
                          </code>
                        ))}
                      </div>
                    </div>
                  )}

                  {threatModel.prd_quotes_analyzed && threatModel.prd_quotes_analyzed.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-void-400 mb-3 flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        Security-Critical PRD Quotes
                      </h4>
                      <div className="space-y-2">
                        {threatModel.prd_quotes_analyzed.slice(0, 10).map((quote, i) => (
                          <div
                            key={i}
                            className="p-3 rounded-lg bg-void-800/50 border border-void-700 text-sm"
                          >
                            {typeof quote === 'string' ? (
                              <p className="text-void-300 italic">"{quote}"</p>
                            ) : (
                              <p className="text-void-300 italic">"{JSON.stringify(quote)}"</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  )
}

function AttackSurfaceRow({ change, index }: { change: AttackSurfaceChange; index: number }) {
  return (
    <motion.tr
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="border-b border-void-800 hover:bg-void-800/30 transition-colors"
    >
      <td className="py-3 px-3">
        <span className="text-white font-medium">{change.component}</span>
      </td>
      <td className="py-3 px-3">
        <span className="text-green-400 text-xs">{change.current_exposure}</span>
      </td>
      <td className="py-3 px-3">
        <span className="text-ember-400 text-xs">{change.proposed_exposure}</span>
      </td>
      <td className="py-3 px-3">
        <span className="text-void-300 text-xs">{change.delta}</span>
      </td>
    </motion.tr>
  )
}
