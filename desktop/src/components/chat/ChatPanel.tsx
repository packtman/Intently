import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Send, X, ExternalLink, Sparkles, Loader2 } from 'lucide-react'
import { useBackend } from '../../hooks/useBackend'

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
  isOpen: boolean
  onClose: () => void
}

export default function ChatPanel({ reviewId, isOpen, onClose }: ChatPanelProps) {
  const { backendUrl } = useBackend()
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

  const sendMessageStreaming = useCallback(async (question: string) => {
    abortRef.current = new AbortController()

    const assistantIdx = messages.length + 1
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }])

    try {
      const res = await fetch(`${backendUrl}/api/chat/stream`, {
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
  }, [messages.length, backendUrl, reviewId, conversationId])

  const sendMessageFallback = useCallback(async (question: string) => {
    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          review_id: reviewId || null,
          conversation_id: conversationId,
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
  }, [backendUrl, reviewId, conversationId])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const question = input.trim()
    const userMessage: ChatMessage = { role: 'user', content: question }
    setMessages(prev => [...prev, userMessage])
    setInput('')
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
    setInput(question)
    setTimeout(() => sendMessage(), 50)
  }

  if (!isOpen) return null

  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="fixed right-0 top-0 h-full w-96 bg-void-900 border-l border-void-700 z-50 flex flex-col shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-void-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-neon-500/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-neon-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Product Chat</h3>
            <p className="text-xs text-void-400">
              {reviewId ? 'Scoped to this review' : 'Ask about your product'}
            </p>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-void-800 text-void-400 hover:text-white transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare className="w-10 h-10 text-void-600 mx-auto mb-3" />
            <p className="text-sm text-void-400 mb-4">Ask anything about your product, codebase, or reviews.</p>
            <div className="space-y-2">
              {['What are the top security findings?', 'What services access PII?', 'How can I improve the PRD quality score?'].map(q => (
                <button
                  key={q}
                  onClick={() => { setInput(q); }}
                  className="block w-full text-left text-xs px-3 py-2 rounded-lg bg-void-800 text-void-300 hover:bg-void-700 hover:text-white transition-colors"
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
                ? 'bg-neon-500/20 text-neon-100 border border-neon-500/30'
                : 'bg-void-800 text-void-200 border border-void-700'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {msg.isStreaming && !msg.content && (
                <Loader2 className="w-4 h-4 text-neon-400 animate-spin" />
              )}

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 pt-2 border-t border-void-700 space-y-1">
                  {msg.citations.slice(0, 3).map((c, j) => (
                    <a
                      key={j}
                      href={c.url}
                      className="flex items-center gap-1.5 text-xs text-neon-400 hover:text-neon-300"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span className="truncate">{c.text}</span>
                    </a>
                  ))}
                </div>
              )}

              {/* Follow-up suggestions */}
              {msg.suggestedFollowups && msg.suggestedFollowups.length > 0 && (
                <div className="mt-2 pt-2 border-t border-void-700 space-y-1">
                  {msg.suggestedFollowups.map((q, j) => (
                    <button
                      key={j}
                      onClick={() => handleFollowup(q)}
                      className="block w-full text-left text-xs px-2 py-1 rounded bg-void-700/50 text-void-300 hover:bg-void-700 hover:text-white transition-colors"
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
            <div className="bg-void-800 border border-void-700 rounded-xl px-3 py-2">
              <Loader2 className="w-4 h-4 text-neon-400 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-void-700">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Ask about your product..."
            className="flex-1 bg-void-800 border border-void-700 rounded-lg px-3 py-2 text-sm text-white placeholder-void-500 focus:outline-none focus:border-neon-500 focus:ring-1 focus:ring-neon-500/30"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="p-2 rounded-lg bg-neon-500 hover:bg-neon-400 disabled:opacity-40 disabled:cursor-not-allowed text-void-950 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-void-500 mt-1.5">Cmd+L to toggle · Answers grounded in your review data</p>
      </div>
    </motion.div>
  )
}
