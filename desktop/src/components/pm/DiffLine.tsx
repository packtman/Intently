/**
 * DiffLine Component - Renders a single line in the side-by-side diff view
 * 
 * Matches the design from SIDE_BY_SIDE_DIFF_PREVIEW.html with:
 * - Line numbers with proper styling
 * - Status-based styling (unchanged, deleted, added, modified, empty)
 * - Word-level change highlighting
 * - Markdown syntax highlighting (headers, bullets, bold)
 * - 3px border-left for changed lines
 */

import { useMemo } from 'react'
import type { DiffLine as DiffLineType } from '../../types'

interface DiffLineProps {
  line: DiffLineType
  side: 'original' | 'suggested'
}

// Highlight markdown syntax in content
function highlightMarkdown(content: string): React.ReactNode {
  // Check for ## headers (cyan)
  if (content.startsWith('## ')) {
    return <span className="text-cyan-400 font-semibold">{content}</span>
  }
  // Check for ### headers (purple)
  if (content.startsWith('### ')) {
    return <span className="text-purple-400 font-medium">{content}</span>
  }
  // Check for bullet points
  if (content.startsWith('- ')) {
    const parts = content.split(/(\*\*[^*]+\*\*)/)
    return (
      <>
        <span className="text-amber-400">-</span>
        {parts.slice(1).map((part, i) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <span key={i} className="text-white font-semibold">{part.slice(2, -2)}</span>
          }
          return <span key={i}>{part}</span>
        })}
      </>
    )
  }
  return content
}

export function DiffLine({ line, side }: DiffLineProps) {
  // Build content with word-level highlighting
  const highlightedContent = useMemo(() => {
    if (!line.word_changes || line.word_changes.length === 0) {
      // Apply markdown highlighting if no word changes
      return highlightMarkdown(line.content)
    }

    const result: React.ReactNode[] = []
    let lastIndex = 0

    // Sort word changes by start position
    const sortedChanges = [...line.word_changes].sort((a, b) => a.start - b.start)

    for (const change of sortedChanges) {
      // Add text before this change
      if (change.start > lastIndex) {
        result.push(line.content.slice(lastIndex, change.start))
      }

      // Add the highlighted change - matching mockup colors
      const changeText = line.content.slice(change.start, change.end)
      const highlightClass =
        change.change_type === 'added'
          ? 'bg-emerald-500/30 px-0.5 rounded-sm'  // rgba(16, 185, 129, 0.3)
          : 'bg-red-500/30 px-0.5 rounded-sm'      // rgba(239, 68, 68, 0.3)

      result.push(
        <span key={`${change.start}-${change.end}`} className={highlightClass}>
          {changeText}
        </span>
      )

      lastIndex = change.end
    }

    // Add remaining text
    if (lastIndex < line.content.length) {
      result.push(line.content.slice(lastIndex))
    }

    return result
  }, [line.content, line.word_changes])

  // Get styling based on line status - matching mockup exactly
  const getLineClasses = () => {
    const baseClasses = 'flex min-h-[1.7em] px-4 font-mono text-[0.85rem] leading-[1.7]'

    switch (line.status) {
      case 'deleted':
        // --diff-del-bg: rgba(239, 68, 68, 0.15), border: rgba(239, 68, 68, 0.4)
        return `${baseClasses} bg-red-500/15 border-l-[3px] border-red-500/40`
      case 'added':
        // --diff-add-bg: rgba(16, 185, 129, 0.15), border: rgba(16, 185, 129, 0.4)
        return `${baseClasses} bg-emerald-500/15 border-l-[3px] border-emerald-500/40`
      case 'modified':
        return side === 'original'
          ? `${baseClasses} bg-red-500/15 border-l-[3px] border-red-500/40`
          : `${baseClasses} bg-emerald-500/15 border-l-[3px] border-emerald-500/40`
      case 'empty':
        // Empty lines have darker background
        return `${baseClasses} bg-black/20 border-l-[3px] border-transparent`
      default:
        return `${baseClasses} border-l-[3px] border-transparent`
    }
  }

  const getContentClasses = () => {
    switch (line.status) {
      case 'deleted':
        // --diff-del-text: #f87171, with strikethrough
        return 'text-red-400 line-through decoration-red-400/50'
      case 'added':
        // --diff-add-text: #34d399
        return 'text-emerald-400'
      case 'modified':
        return side === 'original' ? 'text-red-400 line-through decoration-red-400/50' : 'text-emerald-400'
      case 'empty':
        return 'text-surface-600 italic'
      default:
        return 'text-surface-300'
    }
  }

  return (
    <div className={getLineClasses()}>
      {/* Line number - matching mockup: 45px width, right aligned, muted */}
      <span className="w-[45px] text-right pr-4 text-surface-600 select-none flex-shrink-0 opacity-60">
        {line.line_number ?? ''}
      </span>
      
      {/* Content - with proper word wrapping */}
      <span className={`flex-1 whitespace-pre-wrap break-words pr-4 ${getContentClasses()}`}>
        {line.status === 'empty' ? (
          <span className="text-surface-600 italic">(no content)</span>
        ) : (
          highlightedContent
        )}
      </span>
    </div>
  )
}
