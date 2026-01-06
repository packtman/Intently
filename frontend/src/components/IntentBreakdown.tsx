import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Target,
  Users,
  Database,
  Lock,
  Globe,
  ChevronRight,
  Loader2,
  AlertCircle,
  Sparkles,
  Layers,
  Code,
  Shield,
  Zap,
} from 'lucide-react'

interface ParsedIntent {
  title: string
  summary: string
  features: string[]
  user_stories: string[]
  data_entities: Array<{
    name: string
    type: string
    is_sensitive: boolean
  }>
  api_changes: string[]
  auth_requirements: string[]
  external_integrations: string[]
}

interface IntentBreakdownProps {
  initialContent?: string
  initialTitle?: string
  onContentChange?: (content: string) => void
  onTitleChange?: (title: string) => void
  compact?: boolean
}

export default function IntentBreakdown({
  initialContent = '',
  initialTitle = '',
  onContentChange,
  onTitleChange,
  compact = false,
}: IntentBreakdownProps) {
  const [content, setContent] = useState(initialContent)
  const [title, setTitle] = useState(initialTitle)
  const [parsedIntent, setParsedIntent] = useState<ParsedIntent | null>(null)

  const parseIntent = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/parse-prd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content,
          source_type: 'markdown',
          title: title || 'PRD Analysis',
        }),
      })
      if (!res.ok) throw new Error('Failed to parse PRD')
      return res.json()
    },
    onSuccess: (data) => {
      setParsedIntent(data)
    },
  })

  const handleContentChange = (value: string) => {
    setContent(value)
    onContentChange?.(value)
  }

  const handleTitleChange = (value: string) => {
    setTitle(value)
    onTitleChange?.(value)
  }

  const handleAnalyze = () => {
    setParsedIntent(null)
    parseIntent.mutate()
  }

  return (
    <div className="space-y-6">
      {/* Input Section */}
      {!compact && (
        <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
              <Target className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Intent Breakdown</h2>
              <p className="text-sm text-surface-400">
                Analyze a PRD to understand its security-relevant intent
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => handleTitleChange(e.target.value)}
                placeholder="e.g., User Authentication Feature"
                className="w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                           text-white placeholder-surface-500 focus:border-amber-500 focus:ring-1 
                           focus:ring-amber-500 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                PRD Content (Markdown)
              </label>
              <textarea
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
                placeholder={`# Feature Overview

## Summary
Describe the feature...

## Features
- Feature 1
- Feature 2

## API Changes
- POST /api/users - Create user
- GET /api/users/{id} - Get user

## Security Considerations
- Authentication required
- PII handling`}
                rows={12}
                className="w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                           text-white placeholder-surface-500 focus:border-amber-500 focus:ring-1 
                           focus:ring-amber-500 transition-all font-mono text-sm resize-none"
              />
            </div>

            <button
              onClick={handleAnalyze}
              disabled={!content.trim() || parseIntent.isPending}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 
                         text-white font-medium rounded-lg hover:from-amber-600 hover:to-orange-600 
                         disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {parseIntent.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Analyze Intent
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Compact Mode: Just the button */}
      {compact && content.trim() && (
        <button
          onClick={handleAnalyze}
          disabled={parseIntent.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border border-amber-500/30 
                     text-amber-400 font-medium rounded-lg hover:bg-amber-500/20 
                     disabled:opacity-50 transition-all"
        >
          {parseIntent.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Target className="w-4 h-4" />
              Preview Intent
            </>
          )}
        </button>
      )}

      {/* Error State */}
      {parseIntent.error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-3"
        >
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Analysis Failed</p>
            <p className="text-sm text-red-300">{parseIntent.error.message}</p>
          </div>
        </motion.div>
      )}

      {/* Results Section */}
      <AnimatePresence mode="wait">
        {parsedIntent && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Title & Summary Card */}
            <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-6 h-6 text-amber-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-white mb-2">
                    {parsedIntent.title}
                  </h3>
                  <p className="text-surface-300 leading-relaxed">
                    {parsedIntent.summary || 'No summary extracted'}
                  </p>
                </div>
              </div>
            </div>

            {/* Grid of Sections */}
            <div className="grid grid-cols-2 gap-6">
              {/* Features */}
              <IntentSection
                icon={Layers}
                title="Features"
                items={parsedIntent.features}
                color="primary"
                emptyText="No features identified"
              />

              {/* User Stories */}
              <IntentSection
                icon={Users}
                title="User Stories"
                items={parsedIntent.user_stories}
                color="purple"
                emptyText="No user stories found"
              />

              {/* API Changes */}
              <IntentSection
                icon={Code}
                title="API Changes"
                items={parsedIntent.api_changes}
                color="cyan"
                emptyText="No API changes detected"
              />

              {/* Auth Requirements */}
              <IntentSection
                icon={Lock}
                title="Auth Requirements"
                items={parsedIntent.auth_requirements}
                color="green"
                emptyText="No auth requirements found"
              />

              {/* External Integrations */}
              <IntentSection
                icon={Globe}
                title="External Integrations"
                items={parsedIntent.external_integrations}
                color="blue"
                emptyText="No external integrations"
              />

              {/* Data Entities */}
              <DataEntitiesSection entities={parsedIntent.data_entities} />
            </div>

            {/* Summary Stats */}
            <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
              <h4 className="font-medium text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                Analysis Summary
              </h4>
              <div className="grid grid-cols-5 gap-4">
                <StatBadge
                  label="Features"
                  value={parsedIntent.features.length}
                  color="primary"
                />
                <StatBadge
                  label="User Stories"
                  value={parsedIntent.user_stories.length}
                  color="purple"
                />
                <StatBadge
                  label="API Changes"
                  value={parsedIntent.api_changes.length}
                  color="cyan"
                />
                <StatBadge
                  label="Data Entities"
                  value={parsedIntent.data_entities.length}
                  color="orange"
                />
                <StatBadge
                  label="Sensitive Data"
                  value={parsedIntent.data_entities.filter(e => e.is_sensitive).length}
                  color="red"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function IntentSection({
  icon: Icon,
  title,
  items,
  color,
  emptyText,
}: {
  icon: typeof FileText
  title: string
  items: string[]
  color: string
  emptyText: string
}) {
  const colorClasses: Record<string, string> = {
    primary: 'from-primary-500/20 to-primary-600/10 border-primary-500/30 text-primary-400',
    purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/30 text-purple-400',
    cyan: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/30 text-cyan-400',
    green: 'from-green-500/20 to-green-600/10 border-green-500/30 text-green-400',
    blue: 'from-blue-500/20 to-blue-600/10 border-blue-500/30 text-blue-400',
    orange: 'from-orange-500/20 to-orange-600/10 border-orange-500/30 text-orange-400',
    red: 'from-red-500/20 to-red-600/10 border-red-500/30 text-red-400',
  }

  const iconColors: Record<string, string> = {
    primary: 'text-primary-400',
    purple: 'text-purple-400',
    cyan: 'text-cyan-400',
    green: 'text-green-400',
    blue: 'text-blue-400',
    orange: 'text-orange-400',
    red: 'text-red-400',
  }

  return (
    <div
      className={`bg-gradient-to-br ${colorClasses[color]} rounded-xl border p-5`}
    >
      <div className="flex items-center gap-2 mb-4">
        <Icon className={`w-5 h-5 ${iconColors[color]}`} />
        <h4 className="font-medium text-white">{title}</h4>
        <span className="ml-auto text-sm opacity-60">{items.length}</span>
      </div>
      {items.length > 0 ? (
        <ul className="space-y-2 max-h-48 overflow-y-auto">
          {items.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-sm text-surface-300"
            >
              <ChevronRight className="w-4 h-4 mt-0.5 flex-shrink-0 opacity-50" />
              <span className="line-clamp-2">{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-surface-500 italic">{emptyText}</p>
      )}
    </div>
  )
}

function DataEntitiesSection({
  entities,
}: {
  entities: Array<{ name: string; type: string; is_sensitive: boolean }>
}) {
  return (
    <div className="bg-gradient-to-br from-orange-500/20 to-red-600/10 border-orange-500/30 rounded-xl border p-5">
      <div className="flex items-center gap-2 mb-4">
        <Database className="w-5 h-5 text-orange-400" />
        <h4 className="font-medium text-white">Data Entities</h4>
        <span className="ml-auto text-sm opacity-60">{entities.length}</span>
      </div>
      {entities.length > 0 ? (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {entities.map((entity, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-2 rounded-lg bg-surface-800/50"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm text-white capitalize">{entity.name}</span>
                <span className="px-2 py-0.5 rounded text-xs bg-surface-700 text-surface-300">
                  {entity.type}
                </span>
              </div>
              {entity.is_sensitive && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400 border border-red-500/30">
                  <Shield className="w-3 h-3" />
                  Sensitive
                </span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-surface-500 italic">No data entities identified</p>
      )}
    </div>
  )
}

function StatBadge({
  label,
  value,
  color,
}: {
  label: string
  value: number
  color: string
}) {
  const colorClasses: Record<string, string> = {
    primary: 'bg-primary-500/20 text-primary-400 border-primary-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
  }

  return (
    <div className={`${colorClasses[color]} rounded-lg border p-3 text-center`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs opacity-80">{label}</p>
    </div>
  )
}

