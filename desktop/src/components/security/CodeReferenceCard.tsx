import { motion } from 'framer-motion'
import { FileCode2, AlertTriangle, Lightbulb, ChevronRight, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import type { CodeReference } from '../../types'

interface CodeReferenceCardProps {
  reference: CodeReference
  index?: number
  onOpenFile?: (file: string, line?: number) => void
}

export function CodeReferenceCard({ reference, index = 0, onOpenFile }: CodeReferenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Build file location string
  const fileLocation = (() => {
    let loc = reference.file
    if (reference.line_start) {
      loc += `:${reference.line_start}`
      if (reference.line_end && reference.line_end !== reference.line_start) {
        loc += `-${reference.line_end}`
      }
    }
    return loc
  })()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-xl bg-void-900/50 border border-void-700 overflow-hidden"
    >
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-void-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <FileCode2 className="w-4 h-4 text-neon-400" />
          <div className="flex items-center gap-2">
            <code className="text-sm text-neon-300 bg-neon-500/10 px-2 py-0.5 rounded">
              {fileLocation}
            </code>
            {reference.function_name && (
              <span className="text-xs text-void-400">
                in <code className="text-cyan-400">{reference.function_name}()</code>
              </span>
            )}
            {reference.class_name && (
              <span className="text-xs text-void-400">
                class <code className="text-aurora-400">{reference.class_name}</code>
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onOpenFile && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onOpenFile(reference.file, reference.line_start)
              }}
              className="p-1.5 rounded-lg bg-void-800 border border-void-700 hover:border-neon-500/50 hover:bg-neon-500/10 transition-colors"
              title="Open in editor"
            >
              <ExternalLink className="w-3 h-3 text-neon-400" />
            </button>
          )}
          <ChevronRight
            className={`w-4 h-4 text-void-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          />
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="border-t border-void-700"
        >
          <div className="p-4 space-y-4">
            {/* Issue Description */}
            {reference.issue && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-400 mb-1">Issue</p>
                  <p className="text-sm text-red-200">{reference.issue}</p>
                </div>
              </div>
            )}

            {/* Why Vulnerable */}
            {reference.why_vulnerable && (
              <div className="p-3 rounded-lg bg-ember-500/10 border border-ember-500/30">
                <p className="text-sm font-medium text-ember-400 mb-2">Why This Is Vulnerable</p>
                <p className="text-sm text-ember-200 leading-relaxed">{reference.why_vulnerable}</p>
              </div>
            )}

            {/* Code Snippet */}
            {reference.code_snippet && (
              <div className="rounded-lg bg-void-950 border border-void-700 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 bg-void-900/50 border-b border-void-700">
                  <span className="text-xs font-medium text-void-400">Vulnerable Code</span>
                  {reference.line_start && (
                    <span className="text-xs text-void-500">
                      Line {reference.line_start}
                      {reference.line_end && reference.line_end !== reference.line_start && `-${reference.line_end}`}
                    </span>
                  )}
                </div>
                <pre className="p-3 text-xs text-red-300 font-mono overflow-x-auto whitespace-pre leading-relaxed">
                  {reference.code_snippet}
                </pre>
              </div>
            )}

            {/* Suggested Fix */}
            {reference.suggested_fix && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <Lightbulb className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-green-400 mb-2">Suggested Fix</p>
                  <p className="text-sm text-green-200 leading-relaxed whitespace-pre-wrap">
                    {reference.suggested_fix}
                  </p>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

interface CodeReferencesListProps {
  references: CodeReference[]
  onOpenFile?: (file: string, line?: number) => void
}

export function CodeReferencesList({ references, onOpenFile }: CodeReferencesListProps) {
  if (!references || references.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <FileCode2 className="w-4 h-4 text-neon-400" />
        <span className="text-sm font-medium text-white">
          Code References ({references.length})
        </span>
      </div>
      {references.map((ref, index) => (
        <CodeReferenceCard
          key={`${ref.file}-${ref.line_start || index}`}
          reference={ref}
          index={index}
          onOpenFile={onOpenFile}
        />
      ))}
    </div>
  )
}
