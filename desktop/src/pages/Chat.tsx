import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  MessageSquare,
  Send,
  Sparkles,
  Loader2,
  FolderOpen,
  Code,
  ExternalLink,
  FileCode,
  Zap,
} from 'lucide-react'
import { useBackend } from '../hooks/useBackend'

interface Citation {
  type: string
  id: string
  text: string
  url: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  suggestedFollowups?: string[]
}

interface CodebaseInfo {
  codebase_path: string
  total_indexed_symbols: number
  endpoints: Array<{ name: string; method: string; file: string }>
  data_models: Array<{ name: string; file: string }>
  key_classes: Array<{ name: string; file: string }>
  key_functions: Array<{ name: string; file: string }>
}

export default function Chat() {
  const { backendUrl } = useBackend()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [codebasePath, setCodebasePath] = useState('')
  const [codebaseInfo, setCodebaseInfo] = useState<CodebaseInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isIndexing, setIsIndexing] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleBrowse = async () => {
    if ((window as any).electronAPI?.selectDirectory) {
      const selectedPath = await (window as any).electronAPI.selectDirectory()
      if (selectedPath) {
        setCodebasePath(selectedPath)
      }
    }
  }

  const indexCodebase = async () => {
    if (!codebasePath.trim()) return
    setIsIndexing(true)
    setError(null)

    try {
      const res = await fetch(`${backendUrl}/api/chat/index-codebase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codebase_path: codebasePath.trim() }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setCodebaseInfo(data)
      setMessages([])
      setConversationId(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsIndexing(false)
    }
  }

  const sendMessage = async (overrideQuestion?: string) => {
    const question = overrideQuestion || input.trim()
    if (!question || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content: question }
    setMessages(prev => [...prev, userMessage])
    if (!overrideQuestion) setInput('')
    setIsLoading(true)

    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          conversation_id: conversationId,
          codebase_path: codebasePath.trim() || null,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setConversationId(data.conversation_id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        suggestedFollowups: data.suggested_followups,
      }])
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}`,
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const starterQuestions = [
    'Give me an overview of the codebase architecture',
    'What are the main API endpoints and what do they do?',
    'How does authentication work in this project?',
    'What data models exist and which ones handle PII?',
  ]

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-neon-400" />
          Codebase Chat
        </h1>
        <p className="text-void-400 mt-1">
          Talk to your codebase — ask questions about architecture, endpoints, data models, and patterns
        </p>
      </div>

      {/* Codebase selector */}
      <div className="bg-void-900/50 backdrop-blur-sm rounded-2xl border border-void-800 p-6">
        <label className="block text-sm font-medium text-void-300 mb-2">
          Codebase Path
        </label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <FolderOpen className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
            <input
              type="text"
              value={codebasePath}
              onChange={e => setCodebasePath(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && indexCodebase()}
              placeholder="Enter path to your codebase"
              className="w-full pl-12 pr-4 py-3 bg-void-800 border border-void-700 rounded-lg text-white placeholder-void-500 focus:border-neon-500 focus:ring-1 focus:ring-neon-500 transition-all"
            />
          </div>
          <button
            onClick={handleBrowse}
            className="flex items-center gap-2 px-4 py-3 bg-void-800 border border-void-700 text-void-300 font-medium rounded-lg hover:bg-void-700 hover:border-void-600 transition-all"
          >
            <FolderOpen className="w-4 h-4" />
            Browse
          </button>
          <button
            onClick={indexCodebase}
            disabled={!codebasePath.trim() || isIndexing}
            className="flex items-center gap-2 px-6 py-3 bg-neon-500 text-void-950 font-medium rounded-lg hover:bg-neon-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isIndexing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Indexing...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Connect
              </>
            )}
          </button>
        </div>
        {error && (
          <p className="text-sm text-red-400 mt-2">{error}</p>
        )}

        {codebaseInfo && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 rounded-xl bg-neon-500/10 border border-neon-500/30"
          >
            <div className="flex items-center gap-2 mb-3">
              <Code className="w-4 h-4 text-neon-400" />
              <span className="text-sm font-medium text-neon-400">
                Codebase indexed: {codebaseInfo.total_indexed_symbols} symbols
              </span>
            </div>
            <div className="grid grid-cols-4 gap-3">
              <div className="text-center p-2 bg-void-800/50 rounded-lg">
                <p className="text-lg font-bold text-white">{codebaseInfo.endpoints.length}</p>
                <p className="text-xs text-void-400">Endpoints</p>
              </div>
              <div className="text-center p-2 bg-void-800/50 rounded-lg">
                <p className="text-lg font-bold text-white">{codebaseInfo.data_models.length}</p>
                <p className="text-xs text-void-400">Models</p>
              </div>
              <div className="text-center p-2 bg-void-800/50 rounded-lg">
                <p className="text-lg font-bold text-white">{codebaseInfo.key_classes.length}</p>
                <p className="text-xs text-void-400">Classes</p>
              </div>
              <div className="text-center p-2 bg-void-800/50 rounded-lg">
                <p className="text-lg font-bold text-white">{codebaseInfo.key_functions.length}</p>
                <p className="text-xs text-void-400">Functions</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Chat area */}
      <div className="bg-void-900/50 backdrop-blur-sm rounded-2xl border border-void-800 flex flex-col" style={{ minHeight: '500px' }}>
        <div className="flex-1 overflow-y-auto p-6 space-y-4" style={{ maxHeight: '60vh' }}>
          {messages.length === 0 && (
            <div className="text-center py-12">
              <MessageSquare className="w-12 h-12 text-void-600 mx-auto mb-4" />
              <p className="text-void-400 mb-6">
                {codebaseInfo
                  ? 'Your codebase is connected. Ask anything!'
                  : 'Connect a codebase above, then ask questions about it.'}
              </p>
              {codebaseInfo && (
                <div className="grid grid-cols-2 gap-3 max-w-lg mx-auto">
                  {starterQuestions.map(q => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="text-left text-sm px-4 py-3 rounded-xl bg-void-800 text-void-300 hover:bg-void-700 hover:text-white transition-colors border border-void-700"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-neon-500/20 text-neon-100 border border-neon-500/30'
                  : 'bg-void-800 text-void-200 border border-void-700'
              }`}>
                <MessageContent content={msg.content} />

                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-void-700 space-y-1">
                    {msg.citations.filter(c => c.type === 'code').slice(0, 5).map((c, j) => (
                      <div key={`code-${j}`} className="flex items-center gap-1.5 text-xs text-cyan-400">
                        <FileCode className="w-3 h-3" />
                        <span className="truncate font-mono">{c.text}</span>
                      </div>
                    ))}
                    {msg.citations.filter(c => c.type !== 'code').slice(0, 3).map((c, j) => (
                      <a key={j} href={c.url} className="flex items-center gap-1.5 text-xs text-neon-400 hover:text-neon-300">
                        <ExternalLink className="w-3 h-3" />
                        <span className="truncate">{c.text}</span>
                      </a>
                    ))}
                  </div>
                )}

                {msg.suggestedFollowups && msg.suggestedFollowups.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-void-700 flex flex-wrap gap-2">
                    {msg.suggestedFollowups.map((q, j) => (
                      <button
                        key={j}
                        onClick={() => sendMessage(q)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-void-700/50 text-void-300 hover:bg-void-700 hover:text-white transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-void-800 border border-void-700 rounded-xl px-4 py-3">
                <Loader2 className="w-5 h-5 text-neon-400 animate-spin" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-void-800">
          <div className="flex items-center gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder={codebaseInfo ? 'Ask about your codebase...' : 'Connect a codebase first...'}
              disabled={!codebaseInfo && !codebasePath.trim()}
              className="flex-1 bg-void-800 border border-void-700 rounded-lg px-4 py-3 text-white placeholder-void-500 focus:outline-none focus:border-neon-500 focus:ring-1 focus:ring-neon-500/30 disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="p-3 rounded-lg bg-neon-500 hover:bg-neon-400 disabled:opacity-40 disabled:cursor-not-allowed text-void-950 transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageContent({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g)

  if (parts.length <= 1) {
    return <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
  }

  return (
    <div className="space-y-2">
      {parts.map((part, i) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const inner = part.slice(3, -3)
          const newlineIdx = inner.indexOf('\n')
          const lang = newlineIdx > 0 && newlineIdx < 20 ? inner.slice(0, newlineIdx).trim() : ''
          const code = lang ? inner.slice(newlineIdx + 1) : inner
          return (
            <pre key={i} className="bg-void-950 border border-void-700 rounded-lg p-3 overflow-x-auto text-xs">
              {lang && <div className="text-void-500 text-[10px] mb-1 font-mono">{lang}</div>}
              <code className="text-cyan-300 font-mono">{code}</code>
            </pre>
          )
        }
        return part ? <p key={i} className="whitespace-pre-wrap leading-relaxed">{part}</p> : null
      })}
    </div>
  )
}
