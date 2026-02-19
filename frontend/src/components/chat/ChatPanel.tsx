import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Send, X, ExternalLink, Sparkles, Loader2, FileCode, Code } from 'lucide-react'

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
  isStreaming?: boolean
}

interface ChatPanelProps {
  reviewId?: string
  findingId?: string
  findingTitle?: string
  codebasePath?: string
  isOpen: boolean
  onClose: () => void
}

export default function ChatPanel({ reviewId, findingId, findingTitle, codebasePath, isOpen, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset conversation when finding changes
  useEffect(() => {
    setMessages([])
    setConversationId(null)
  }, [findingId])

  const sendMessageStreaming = useCallback(async (question: string) => {
    abortRef.current = new AbortController()

    const assistantIdx = messages.length + 1
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }])

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          review_id: reviewId || null,
          conversation_id: conversationId,
        }),
        signal: abortRef.current.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const event = JSON.parse(jsonStr)

            if (event.done) {
              setMessages(prev => prev.map((msg, i) =>
                i === assistantIdx
                  ? {
                      ...msg,
                      isStreaming: false,
                      citations: event.citations || [],
                      suggestedFollowups: event.suggested_followups || [],
                    }
                  : msg
              ))
              if (event.conversation_id) {
                setConversationId(event.conversation_id)
              }
            } else if (event.token !== undefined) {
              setMessages(prev => prev.map((msg, i) =>
                i === assistantIdx
                  ? { ...msg, content: msg.content + event.token }
                  : msg
              ))
            }
          } catch {
            // skip malformed JSON lines
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return
      throw err
    }
  }, [messages.length, reviewId, conversationId])

  const sendMessageFallback = useCallback(async (question: string) => {
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          review_id: reviewId || null,
          conversation_id: conversationId,
          finding_id: findingId || null,
          codebase_path: codebasePath || null,
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
        content: `Error: ${err.message}. Make sure FEATURE_PRODUCT_CHAT=true and an LLM API key is set.`,
      }])
    }
  }, [reviewId, conversationId])

  const sendMessage = async (overrideQuestion?: string) => {
    const question = overrideQuestion || input.trim()
    if (!question || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content: question }
    setMessages(prev => [...prev, userMessage])
    if (!overrideQuestion) setInput('')
    setIsLoading(true)

    try {
      await sendMessageStreaming(question)
    } catch {
      await sendMessageFallback(question)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFollowup = (question: string) => {
    sendMessage(question)
  }

  if (!isOpen) return null

  const subtitle = findingTitle
    ? `Finding: ${findingTitle}`
    : reviewId
      ? 'Scoped to this review'
      : codebasePath
        ? 'Exploring codebase'
        : 'Ask about your product'

  const starterQuestions = findingId
    ? [
        'Explain this finding in simpler business terms',
        "What's the minimum fix to unblock shipping?",
        'Write me a ticket description for this',
      ]
    : codebasePath || reviewId
      ? [
          'How does authentication work in this codebase?',
          'What are the main API endpoints?',
          'Which data models handle sensitive data?',
        ]
      : [
          'What are the top security findings?',
          'What services access PII?',
          'How can I improve the PRD quality score?',
        ]

  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="fixed right-0 top-0 h-full w-96 bg-surface-900 border-l border-surface-700 z-50 flex flex-col shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-700">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center flex-shrink-0">
            {findingId ? <FileCode className="w-4 h-4 text-primary-400" /> : <Sparkles className="w-4 h-4 text-primary-400" />}
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-white">
              {findingId ? 'Finding Chat' : 'Product Chat'}
            </h3>
            <p className="text-xs text-surface-400 truncate">{subtitle}</p>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-800 text-surface-400 hover:text-white transition-colors flex-shrink-0">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare className="w-10 h-10 text-surface-600 mx-auto mb-3" />
            <p className="text-sm text-surface-400 mb-4">
              {findingId
                ? 'Ask anything about this finding.'
                : 'Ask anything about your product, codebase, or reviews.'}
            </p>
            <div className="space-y-2">
              {starterQuestions.map(q => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="block w-full text-left text-xs px-3 py-2 rounded-lg bg-surface-800 text-surface-300 hover:bg-surface-700 hover:text-white transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
              msg.role === 'user'
                ? 'bg-primary-500/20 text-primary-100 border border-primary-500/30'
                : 'bg-surface-800 text-surface-200 border border-surface-700'
            }`}>
              <MessageContent content={msg.content} />

              {msg.isStreaming && !msg.content && (
                <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
              )}

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 pt-2 border-t border-surface-700 space-y-1">
                  {msg.citations.filter(c => c.type !== 'code').slice(0, 3).map((c, j) => (
                    <a
                      key={j}
                      href={c.url}
                      className="flex items-center gap-1.5 text-xs text-primary-400 hover:text-primary-300"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span className="truncate">{c.text}</span>
                    </a>
                  ))}
                  {msg.citations.filter(c => c.type === 'code').slice(0, 3).map((c, j) => (
                    <div
                      key={`code-${j}`}
                      className="flex items-center gap-1.5 text-xs text-cyan-400"
                    >
                      <Code className="w-3 h-3" />
                      <span className="truncate font-mono">{c.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Follow-up suggestions */}
              {msg.suggestedFollowups && msg.suggestedFollowups.length > 0 && (
                <div className="mt-2 pt-2 border-t border-surface-700 space-y-1">
                  {msg.suggestedFollowups.map((q, j) => (
                    <button
                      key={j}
                      onClick={() => handleFollowup(q)}
                      className="block w-full text-left text-xs px-2 py-1 rounded bg-surface-700/50 text-surface-300 hover:bg-surface-700 hover:text-white transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex justify-start">
            <div className="bg-surface-800 border border-surface-700 rounded-xl px-3 py-2">
              <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-surface-700">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder={findingId ? 'Ask about this finding...' : 'Ask about your product...'}
            className="flex-1 bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white placeholder-surface-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/30"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="p-2 rounded-lg bg-primary-500 hover:bg-primary-600 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-surface-500 mt-1.5">
          {(codebasePath || reviewId) ? 'Answers grounded in your codebase + review data' : 'Answers grounded in your review data'}
        </p>
      </div>
    </motion.div>
  )
}

function MessageContent({ content }: { content: string }) {
  // Split message into text and code blocks for rendering
  const parts = content.split(/(```[\s\S]*?```)/g)

  if (parts.length <= 1) {
    return <p className="whitespace-pre-wrap">{content}</p>
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
            <pre key={i} className="bg-surface-900 border border-surface-700 rounded-lg p-2 overflow-x-auto text-xs">
              {lang && <div className="text-surface-500 text-[10px] mb-1 font-mono">{lang}</div>}
              <code className="text-cyan-300 font-mono">{code}</code>
            </pre>
          )
        }
        return part ? <p key={i} className="whitespace-pre-wrap">{part}</p> : null
      })}
    </div>
  )
}
