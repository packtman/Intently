import { useEffect, useRef, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Terminal,
  ChevronDown,
  ChevronUp,
  Circle,
  AlertTriangle,
  AlertCircle,
  Info,
  Bug,
  Filter,
  X,
} from 'lucide-react'

interface TraceEvent {
  timestamp: string
  elapsed_ms: number
  level: string
  phase: string
  message: string
  metadata: Record<string, unknown>
}

interface TraceLogPanelProps {
  traceId: string
  endpoint: string
  isRunning?: boolean
  defaultCollapsed?: boolean
}

const PHASE_COLORS: Record<string, string> = {
  init: 'text-void-400',
  prd_parse: 'text-neon-400',
  codebase_analysis: 'text-blue-400',
  llm_dispatch: 'text-aurora-400',
  fp_filter: 'text-yellow-400',
  report_gen: 'text-green-400',
  bulk: 'text-orange-400',
}

const PHASE_LABELS: Record<string, string> = {
  init: 'INIT',
  prd_parse: 'PRD',
  codebase_analysis: 'CODE',
  llm_dispatch: 'LLM',
  fp_filter: 'FP',
  report_gen: 'REPORT',
  bulk: 'BULK',
}

const LEVEL_ICONS: Record<string, typeof Info> = {
  info: Info,
  debug: Bug,
  warn: AlertTriangle,
  error: AlertCircle,
}

const LEVEL_COLORS: Record<string, string> = {
  info: 'text-void-300',
  debug: 'text-void-500',
  warn: 'text-yellow-400',
  error: 'text-red-400',
}

export default function TraceLogPanel({
  traceId,
  endpoint,
  isRunning = true,
  defaultCollapsed = false,
}: TraceLogPanelProps) {
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const [autoScroll, setAutoScroll] = useState(true)
  const [phaseFilter, setPhaseFilter] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const isRunningRef = useRef(isRunning)
  isRunningRef.current = isRunning

  useEffect(() => {
    if (!traceId || !endpoint) return

    const es = new EventSource(endpoint)
    eventSourceRef.current = es

    es.onmessage = (e) => {
      try {
        const event: TraceEvent = JSON.parse(e.data)
        setEvents((prev) => [...prev, event])
      } catch {
        // ignore parse errors
      }
    }

    es.addEventListener('done', () => {
      setDone(true)
      es.close()
    })

    es.onerror = () => {
      if (!isRunningRef.current) {
        setDone(true)
        es.close()
      }
    }

    return () => {
      es.close()
      eventSourceRef.current = null
    }
  }, [traceId, endpoint])

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events, autoScroll])

  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 40)
  }, [])

  const filteredEvents = phaseFilter
    ? events.filter((e) => e.phase === phaseFilter)
    : events

  const uniquePhases = [...new Set(events.map((e) => e.phase))]

  const formatElapsed = (ms: number) => {
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-void-900 border border-void-700 rounded-xl overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 bg-void-800/50 hover:bg-void-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Terminal className="w-4 h-4 text-neon-400" />
          <span className="text-sm font-medium text-void-200">
            Trace Log
          </span>
          <span className="text-xs text-void-500">
            {events.length} events
          </span>
          {!done && isRunning && (
            <span className="flex items-center gap-1 text-xs text-neon-400">
              <Circle className="w-2 h-2 fill-neon-400 animate-pulse" />
              Live
            </span>
          )}
          {done && (
            <span className="text-xs text-green-400">Complete</span>
          )}
        </div>
        {collapsed ? (
          <ChevronDown className="w-4 h-4 text-void-400" />
        ) : (
          <ChevronUp className="w-4 h-4 text-void-400" />
        )}
      </button>

      {/* Body */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {/* Phase filter bar */}
            {uniquePhases.length > 1 && (
              <div className="flex items-center gap-2 px-4 py-2 border-b border-void-700/50 overflow-x-auto">
                <Filter className="w-3 h-3 text-void-500 flex-shrink-0" />
                <button
                  onClick={() => setPhaseFilter(null)}
                  className={`px-2 py-0.5 rounded text-xs transition-colors ${
                    !phaseFilter
                      ? 'bg-neon-500/20 text-neon-300'
                      : 'text-void-400 hover:text-void-200'
                  }`}
                >
                  All
                </button>
                {uniquePhases.map((phase) => (
                  <button
                    key={phase}
                    onClick={() =>
                      setPhaseFilter(phaseFilter === phase ? null : phase)
                    }
                    className={`px-2 py-0.5 rounded text-xs transition-colors flex items-center gap-1 ${
                      phaseFilter === phase
                        ? 'bg-neon-500/20 text-neon-300'
                        : 'text-void-400 hover:text-void-200'
                    }`}
                  >
                    <span className={PHASE_COLORS[phase] || 'text-void-400'}>
                      {PHASE_LABELS[phase] || phase.toUpperCase()}
                    </span>
                    {phaseFilter === phase && (
                      <X className="w-3 h-3" />
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* Events list */}
            <div
              ref={scrollRef}
              onScroll={handleScroll}
              className="max-h-80 overflow-y-auto font-mono text-xs leading-relaxed"
            >
              {filteredEvents.length === 0 && (
                <div className="px-4 py-8 text-center text-void-500">
                  {isRunning
                    ? 'Waiting for trace events...'
                    : 'No trace events recorded.'}
                </div>
              )}
              {filteredEvents.map((event, i) => {
                const LevelIcon = LEVEL_ICONS[event.level] || Info
                const levelColor = LEVEL_COLORS[event.level] || 'text-void-400'
                const phaseColor = PHASE_COLORS[event.phase] || 'text-void-400'
                const phaseLabel = PHASE_LABELS[event.phase] || event.phase.toUpperCase()

                return (
                  <div
                    key={i}
                    className={`flex items-start gap-2 px-4 py-1.5 hover:bg-void-800/30 transition-colors border-b border-void-800/30 ${
                      event.level === 'error'
                        ? 'bg-red-500/5'
                        : event.level === 'warn'
                        ? 'bg-yellow-500/5'
                        : ''
                    }`}
                  >
                    <span className="text-void-600 w-14 text-right flex-shrink-0 tabular-nums">
                      {formatElapsed(event.elapsed_ms)}
                    </span>
                    <LevelIcon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${levelColor}`} />
                    <span
                      className={`px-1.5 py-0 rounded text-[10px] font-bold flex-shrink-0 bg-void-800 ${phaseColor}`}
                    >
                      {phaseLabel}
                    </span>
                    <span className="text-void-300 break-words min-w-0">
                      {event.message}
                    </span>
                  </div>
                )
              })}

              {done && filteredEvents.length > 0 && (
                <div className="px-4 py-2 text-center text-xs text-void-600 border-t border-void-700/50">
                  Scan complete &mdash; {events.length} trace events recorded
                  {events.length > 0 &&
                    ` in ${formatElapsed(events[events.length - 1].elapsed_ms)}`}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
