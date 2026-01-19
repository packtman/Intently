import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  Target,
  Shield,
  FileText,
  Gauge,
  Hash,
} from 'lucide-react'
import { AttackFlowDiagram } from './AttackFlowDiagram'
import { CodeReferencesList } from './CodeReferenceCard'
import { RemediationStrategy } from './RemediationStrategy'
import type { Finding } from '../../types'

interface EnhancedFindingDetailsProps {
  finding: Finding
  onOpenFile?: (file: string, line?: number) => void
}

export function EnhancedFindingDetails({ finding, onOpenFile }: EnhancedFindingDetailsProps) {
  const hasEnhancedData =
    finding.attack_flow_diagram ||
    (finding.attack_flow_steps && finding.attack_flow_steps.length > 0) ||
    (finding.code_references && finding.code_references.length > 0) ||
    finding.remediation ||
    finding.prd_trigger ||
    finding.evidence ||
    finding.impact_analysis ||
    finding.cvss_estimate

  if (!hasEnhancedData) return null

  const likelihoodColors: Record<string, string> = {
    HIGH: 'bg-red-500/20 text-red-400',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400',
    LOW: 'bg-green-500/20 text-green-400',
  }

  return (
    <div className="space-y-4 pt-4 border-t border-void-700">
      {/* STRIDE & CVSS Metadata */}
      {(finding.stride_category || finding.likelihood || finding.cvss_estimate) && (
        <div className="flex flex-wrap items-center gap-3">
          {finding.stride_category && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <Shield className="w-3 h-3 text-purple-400" />
              <span className="text-xs text-purple-300">STRIDE: {finding.stride_category}</span>
            </div>
          )}
          {finding.likelihood && (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${likelihoodColors[finding.likelihood] || 'bg-void-700 text-void-300'}`}>
              <Target className="w-3 h-3" />
              <span className="text-xs font-medium">{finding.likelihood} Likelihood</span>
            </div>
          )}
          {finding.cvss_estimate !== undefined && finding.cvss_estimate > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-void-700">
              <Gauge className="w-3 h-3 text-neon-400" />
              <span className="text-xs text-void-300">CVSS:</span>
              <CvssScore score={finding.cvss_estimate} />
            </div>
          )}
        </div>
      )}

      {/* PRD Trigger */}
      {finding.prd_trigger && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30"
        >
          <div className="flex items-start gap-3">
            <FileText className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-400 mb-2">PRD Trigger</p>
              <blockquote className="text-sm text-amber-200 italic border-l-2 border-amber-500/50 pl-3">
                "{finding.prd_trigger}"
              </blockquote>
            </div>
          </div>
        </motion.div>
      )}

      {/* Evidence */}
      {finding.evidence && (finding.evidence.prd_references?.length || finding.evidence.code_evidence) && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-void-800/50 border border-void-700"
        >
          <div className="flex items-center gap-2 mb-3">
            <Hash className="w-4 h-4 text-neon-400" />
            <span className="text-sm font-medium text-white">Evidence</span>
          </div>
          
          {finding.evidence.prd_references && finding.evidence.prd_references.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-void-400 mb-2">PRD References</p>
              <ul className="space-y-1">
                {finding.evidence.prd_references.map((ref, i) => (
                  <li key={i} className="text-sm text-void-300 flex items-start gap-2">
                    <span className="text-neon-400">-</span>
                    {ref}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {finding.evidence.code_evidence && (
            <div>
              <p className="text-xs text-void-400 mb-2">Code Evidence</p>
              <p className="text-sm text-void-300">{finding.evidence.code_evidence}</p>
            </div>
          )}
        </motion.div>
      )}

      {/* Impact Analysis */}
      {finding.impact_analysis && Object.keys(finding.impact_analysis).length > 0 && (
        <ImpactAnalysisCard impact={finding.impact_analysis} />
      )}

      {/* Technical Details Enhanced */}
      {finding.technical_details_enhanced && Object.keys(finding.technical_details_enhanced).length > 0 && (
        <TechnicalDetailsCard details={finding.technical_details_enhanced} />
      )}

      {/* Attack Flow */}
      {(finding.attack_flow_diagram || (finding.attack_flow_steps && finding.attack_flow_steps.length > 0)) && (
        <AttackFlowDiagram
          diagram={finding.attack_flow_diagram}
          steps={finding.attack_flow_steps}
        />
      )}

      {/* Code References */}
      {finding.code_references && finding.code_references.length > 0 && (
        <CodeReferencesList references={finding.code_references} onOpenFile={onOpenFile} />
      )}

      {/* Remediation Strategy */}
      {finding.remediation && <RemediationStrategy remediation={finding.remediation} />}

      {/* Legacy Mitigations (fallback) */}
      {!finding.remediation && finding.required_mitigations && finding.required_mitigations.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-green-500/10 border border-green-500/30"
        >
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-green-400" />
            <span className="text-sm font-medium text-green-400">Required Mitigations</span>
          </div>
          <ul className="space-y-2">
            {finding.required_mitigations.map((m, i) => (
              <li key={i} className="text-sm text-green-200 flex items-start gap-2">
                <span className="text-green-400 mt-0.5">-</span>
                <div>
                  <span className="font-medium">{m.action || String(m)}</span>
                  {m.owner && <span className="text-green-400/70 ml-2">(Owner: {m.owner})</span>}
                  {m.effort && <span className="text-green-400/70 ml-2">Effort: {m.effort}</span>}
                </div>
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </div>
  )
}

function CvssScore({ score }: { score: number }) {
  const getColor = () => {
    if (score >= 9.0) return 'text-red-400 bg-red-500/30'
    if (score >= 7.0) return 'text-ember-400 bg-ember-500/30'
    if (score >= 4.0) return 'text-yellow-400 bg-yellow-500/30'
    return 'text-green-400 bg-green-500/30'
  }

  const getLabel = () => {
    if (score >= 9.0) return 'Critical'
    if (score >= 7.0) return 'High'
    if (score >= 4.0) return 'Medium'
    return 'Low'
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${getColor()}`}>
      {score.toFixed(1)} ({getLabel()})
    </span>
  )
}

function ImpactAnalysisCard({ impact }: { impact: Finding['impact_analysis'] }) {
  if (!impact) return null

  const impactLevelColors: Record<string, string> = {
    HIGH: 'text-red-400',
    MEDIUM: 'text-yellow-400',
    LOW: 'text-green-400',
    NONE: 'text-void-500',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-void-800/50 border border-void-700"
    >
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-ember-400" />
        <span className="text-sm font-medium text-white">Impact Analysis</span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        {impact.confidentiality && (
          <div className="text-center p-3 rounded-lg bg-void-900/50">
            <p className="text-xs text-void-400 mb-1">Confidentiality</p>
            <p className={`text-sm font-medium ${impactLevelColors[impact.confidentiality.split(':')[0]?.toUpperCase()] || 'text-void-300'}`}>
              {impact.confidentiality.split(':')[0]}
            </p>
          </div>
        )}
        {impact.integrity && (
          <div className="text-center p-3 rounded-lg bg-void-900/50">
            <p className="text-xs text-void-400 mb-1">Integrity</p>
            <p className={`text-sm font-medium ${impactLevelColors[impact.integrity.split(':')[0]?.toUpperCase()] || 'text-void-300'}`}>
              {impact.integrity.split(':')[0]}
            </p>
          </div>
        )}
        {impact.availability && (
          <div className="text-center p-3 rounded-lg bg-void-900/50">
            <p className="text-xs text-void-400 mb-1">Availability</p>
            <p className={`text-sm font-medium ${impactLevelColors[impact.availability.split(':')[0]?.toUpperCase()] || 'text-void-300'}`}>
              {impact.availability.split(':')[0]}
            </p>
          </div>
        )}
      </div>

      {impact.business_impact && (
        <div className="p-3 rounded-lg bg-ember-500/10 border border-ember-500/30 mb-2">
          <p className="text-xs text-ember-400 mb-1">Business Impact</p>
          <p className="text-sm text-ember-200">{impact.business_impact}</p>
        </div>
      )}

      {impact.user_impact && (
        <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30 mb-2">
          <p className="text-xs text-purple-400 mb-1">User Impact</p>
          <p className="text-sm text-purple-200">{impact.user_impact}</p>
        </div>
      )}

      {impact.regulatory_impact && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
          <p className="text-xs text-red-400 mb-1">Regulatory Impact</p>
          <p className="text-sm text-red-200">{impact.regulatory_impact}</p>
        </div>
      )}
    </motion.div>
  )
}

function TechnicalDetailsCard({ details }: { details: Finding['technical_details_enhanced'] }) {
  if (!details) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-cyan-500/5 border border-cyan-500/30"
    >
      <div className="flex items-center gap-2 mb-4">
        <Target className="w-4 h-4 text-cyan-400" />
        <span className="text-sm font-medium text-white">Technical Details</span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {details.attack_vector && (
          <div>
            <p className="text-xs text-void-400">Attack Vector</p>
            <p className="text-sm text-white">{details.attack_vector}</p>
          </div>
        )}
        {details.attack_complexity && (
          <div>
            <p className="text-xs text-void-400">Complexity</p>
            <p className="text-sm text-white">{details.attack_complexity}</p>
          </div>
        )}
        {details.privileges_required && (
          <div>
            <p className="text-xs text-void-400">Privileges Required</p>
            <p className="text-sm text-white">{details.privileges_required}</p>
          </div>
        )}
        {details.user_interaction && (
          <div>
            <p className="text-xs text-void-400">User Interaction</p>
            <p className="text-sm text-white">{details.user_interaction}</p>
          </div>
        )}
      </div>

      {details.prerequisites && details.prerequisites.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-void-400 mb-2">Prerequisites</p>
          <div className="flex flex-wrap gap-2">
            {details.prerequisites.map((p, i) => (
              <span key={i} className="text-xs text-cyan-300 bg-cyan-500/10 px-2 py-1 rounded">
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {details.affected_endpoints && details.affected_endpoints.length > 0 && (
        <div>
          <p className="text-xs text-void-400 mb-2">Affected Endpoints</p>
          <div className="flex flex-wrap gap-2">
            {details.affected_endpoints.map((ep, i) => (
              <code key={i} className="text-xs text-neon-300 bg-neon-500/10 px-2 py-1 rounded font-mono">
                {ep}
              </code>
            ))}
          </div>
        </div>
      )}

      {details.data_at_risk && details.data_at_risk.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-void-400 mb-2">Data at Risk</p>
          <div className="flex flex-wrap gap-2">
            {details.data_at_risk.map((d, i) => (
              <span key={i} className="text-xs text-red-300 bg-red-500/10 px-2 py-1 rounded">
                {d}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
