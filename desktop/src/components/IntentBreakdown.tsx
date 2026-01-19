import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Target,
  Layers,
  Code,
  Database,
  Users,
  Lock,
  Globe,
  Shield,
  AlertCircle,
  Loader2,
  Upload,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { api } from '../services/api'
import { useBackend } from '../hooks/useBackend'
import type { ParsedIntent } from '../types'

export default function IntentBreakdown() {
  const { isConnected } = useBackend()
  const [prdContent, setPrdContent] = useState('')
  const [intent, setIntent] = useState<ParsedIntent | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary']))

  const parseIntent = useMutation({
    mutationFn: async () => {
      return api.parsePRD(prdContent, 'PRD Analysis')
    },
    onSuccess: (data) => {
      setIntent(data)
    },
  })

  const selectFile = async () => {
    const path = await window.electronAPI?.selectFile([
      { name: 'Markdown', extensions: ['md', 'markdown'] },
      { name: 'Text', extensions: ['txt'] },
    ])
    if (path) {
      const content = await window.electronAPI?.readFile(path)
      if (content) {
        setPrdContent(content)
      }
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <AlertCircle className="w-12 h-12 text-ember-400 mb-4" />
        <p className="text-void-400">Backend required for intent analysis</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Input Section */}
      <div className="card-glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-ember-500/20 flex items-center justify-center">
              <Target className="w-5 h-5 text-ember-400" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-white">PRD Intent Analyzer</h3>
              <p className="text-sm text-void-400">Extract structured intent from your PRD</p>
            </div>
          </div>
          <button onClick={selectFile} className="btn-secondary flex items-center gap-2 text-sm">
            <Upload className="w-4 h-4" />
            Load File
          </button>
        </div>

        <textarea
          value={prdContent}
          onChange={(e) => setPrdContent(e.target.value)}
          placeholder="Paste your PRD content here..."
          rows={8}
          className="input-field font-mono text-sm resize-none"
        />

        <div className="flex justify-end">
          <button
            onClick={() => parseIntent.mutate()}
            disabled={!prdContent.trim() || parseIntent.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {parseIntent.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Target className="w-5 h-5" />
                Analyze Intent
              </>
            )}
          </button>
        </div>

        {parseIntent.error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-sm text-red-300">{parseIntent.error.message}</p>
          </div>
        )}
      </div>

      {/* Results Section */}
      <AnimatePresence>
        {intent && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-4"
          >
            {/* Stats Row */}
            <div className="grid grid-cols-4 gap-4">
              <StatBox icon={Layers} label="Features" value={intent.features.length} color="neon" />
              <StatBox icon={Code} label="API Changes" value={intent.api_changes.length} color="aurora" />
              <StatBox icon={Database} label="Data Entities" value={intent.data_entities.length} color="ember" />
              <StatBox
                icon={Shield}
                label="Sensitive Data"
                value={intent.data_entities.filter((e) => e.is_sensitive).length}
                color="red"
              />
            </div>

            {/* Summary */}
            <CollapsibleSection
              title="Summary"
              icon={Target}
              isExpanded={expandedSections.has('summary')}
              onToggle={() => toggleSection('summary')}
            >
              <div className="space-y-3">
                <h4 className="font-semibold text-white text-lg">{intent.title}</h4>
                {intent.summary && <p className="text-void-300 leading-relaxed">{intent.summary}</p>}
              </div>
            </CollapsibleSection>

            {/* Features */}
            {intent.features.length > 0 && (
              <CollapsibleSection
                title={`Features (${intent.features.length})`}
                icon={Layers}
                isExpanded={expandedSections.has('features')}
                onToggle={() => toggleSection('features')}
              >
                <ul className="space-y-2">
                  {intent.features.map((feature, i) => (
                    <li key={i} className="flex items-start gap-2 text-void-300">
                      <span className="text-neon-400 mt-1">*</span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            )}

            {/* User Stories */}
            {intent.user_stories.length > 0 && (
              <CollapsibleSection
                title={`User Stories (${intent.user_stories.length})`}
                icon={Users}
                isExpanded={expandedSections.has('stories')}
                onToggle={() => toggleSection('stories')}
              >
                <ul className="space-y-2">
                  {intent.user_stories.map((story, i) => (
                    <li key={i} className="p-3 rounded-xl bg-void-800/50 border border-void-700 text-void-300 text-sm">
                      {story}
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            )}

            {/* API Changes */}
            {intent.api_changes.length > 0 && (
              <CollapsibleSection
                title={`API Changes (${intent.api_changes.length})`}
                icon={Code}
                isExpanded={expandedSections.has('api')}
                onToggle={() => toggleSection('api')}
              >
                <ul className="space-y-2">
                  {intent.api_changes.map((change, i) => (
                    <li
                      key={i}
                      className="flex items-center gap-2 p-2 rounded-lg bg-aurora-500/10 border border-aurora-500/30 font-mono text-sm text-aurora-300"
                    >
                      <Code className="w-4 h-4 text-aurora-400" />
                      {change}
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            )}

            {/* Data Entities */}
            {intent.data_entities.length > 0 && (
              <CollapsibleSection
                title={`Data Entities (${intent.data_entities.length})`}
                icon={Database}
                isExpanded={expandedSections.has('data')}
                onToggle={() => toggleSection('data')}
              >
                <div className="grid grid-cols-2 gap-3">
                  {intent.data_entities.map((entity, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-xl border ${
                        entity.is_sensitive
                          ? 'bg-red-500/10 border-red-500/30'
                          : 'bg-void-800/50 border-void-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-white">{entity.name}</span>
                        {entity.is_sensitive && (
                          <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-xs">
                            Sensitive
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-void-400">{entity.type}</span>
                    </div>
                  ))}
                </div>
              </CollapsibleSection>
            )}

            {/* Auth Requirements */}
            {intent.auth_requirements.length > 0 && (
              <CollapsibleSection
                title={`Auth Requirements (${intent.auth_requirements.length})`}
                icon={Lock}
                isExpanded={expandedSections.has('auth')}
                onToggle={() => toggleSection('auth')}
              >
                <ul className="space-y-2">
                  {intent.auth_requirements.map((req, i) => (
                    <li key={i} className="flex items-center gap-2 text-void-300">
                      <Lock className="w-4 h-4 text-neon-400" />
                      {req}
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            )}

            {/* External Integrations */}
            {intent.external_integrations.length > 0 && (
              <CollapsibleSection
                title={`External Integrations (${intent.external_integrations.length})`}
                icon={Globe}
                isExpanded={expandedSections.has('integrations')}
                onToggle={() => toggleSection('integrations')}
              >
                <div className="flex flex-wrap gap-2">
                  {intent.external_integrations.map((integration, i) => (
                    <span
                      key={i}
                      className="px-3 py-1.5 rounded-lg bg-void-800 border border-void-700 text-void-300 text-sm"
                    >
                      {integration}
                    </span>
                  ))}
                </div>
              </CollapsibleSection>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function StatBox({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Layers
  label: string
  value: number
  color: string
}) {
  const colorClasses: Record<string, string> = {
    neon: 'bg-neon-500/10 text-neon-400 border-neon-500/30',
    aurora: 'bg-aurora-500/10 text-aurora-400 border-aurora-500/30',
    ember: 'bg-ember-500/10 text-ember-400 border-ember-500/30',
    red: 'bg-red-500/10 text-red-400 border-red-500/30',
  }

  return (
    <div className={`${colorClasses[color]} rounded-xl border p-4 text-center`}>
      <Icon className="w-5 h-5 mx-auto mb-2" />
      <p className="text-2xl font-display font-bold text-white">{value}</p>
      <p className="text-xs opacity-80">{label}</p>
    </div>
  )
}

function CollapsibleSection({
  title,
  icon: Icon,
  isExpanded,
  onToggle,
  children,
}: {
  title: string
  icon: typeof Layers
  isExpanded: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="card-glass rounded-2xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-void-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-neon-400" />
          <span className="font-medium text-white">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-void-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-void-400" />
        )}
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 pt-0">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

