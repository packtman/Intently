/**
 * Expert Ask Modal - Quick ask to an expert (not a ticket)
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Send, Search, User } from 'lucide-react'
import { api } from '../../services/api'

interface ExpertAskModalProps {
  isOpen: boolean
  onClose: () => void
  predictionId: string
  defaultQuestion: string
  reviewId: string
}

// Mock experts - in production, this would come from API
const MOCK_EXPERTS = [
  { id: 'expert-1', name: 'Bob Wilson', domain: 'devops', expertise: ['rate limiting', 'infrastructure'] },
  { id: 'expert-2', name: 'Sarah Chen', domain: 'security', expertise: ['authentication', 'authorization'] },
  { id: 'expert-3', name: 'Mike Johnson', domain: 'engineering', expertise: ['api design', 'scalability'] },
]

export function ExpertAskModal({
  isOpen,
  onClose,
  predictionId,
  defaultQuestion,
  reviewId,
}: ExpertAskModalProps) {
  const [selectedExpert, setSelectedExpert] = useState<string | null>(null)
  const [question, setQuestion] = useState(defaultQuestion)
  const [searchQuery, setSearchQuery] = useState('')

  const askMutation = useMutation({
    mutationFn: (request: { prediction_id: string; expert_id: string; expert_name: string; question: string }) =>
      api.askExpert(request),
    onSuccess: () => {
      onClose()
      // Show success notification
    },
  })

  const filteredExperts = MOCK_EXPERTS.filter((expert) =>
    expert.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    expert.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
    expert.expertise.some((e) => e.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const handleSend = () => {
    if (!selectedExpert) return

    const expert = MOCK_EXPERTS.find((e) => e.id === selectedExpert)
    if (!expert) return

    askMutation.mutate({
      prediction_id: predictionId,
      expert_id: expert.id,
      expert_name: expert.name,
      question,
    })
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-void-900 rounded-2xl border border-void-700 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="p-6 border-b border-void-800 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">Quick Ask</h2>
              <p className="text-sm text-void-400 mt-1">
                Ping an expert for quick validation (not a formal review)
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-void-500 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Expert Search */}
            <div>
              <label className="block text-sm font-medium text-void-300 mb-2">
                Ask someone who knows:
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search experts..."
                  className="w-full pl-10 pr-4 py-2 bg-void-800 border border-void-700 rounded-lg
                           text-white placeholder-void-500 focus:border-neon-500 focus:ring-1
                           focus:ring-neon-500"
                />
              </div>

              {/* Expert List */}
              <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                {filteredExperts.map((expert) => (
                  <button
                    key={expert.id}
                    onClick={() => setSelectedExpert(expert.id)}
                    className={`
                      w-full p-3 rounded-lg border text-left transition-all
                      ${selectedExpert === expert.id
                        ? 'bg-neon-500/20 border-neon-500/50'
                        : 'bg-void-800 border-void-700 hover:border-void-600'
                      }
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-neon-500/20 flex items-center justify-center">
                        <User className="w-5 h-5 text-neon-400" />
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-white">{expert.name}</div>
                        <div className="text-sm text-void-400 capitalize">{expert.domain}</div>
                        <div className="text-xs text-void-500 mt-1">
                          {expert.expertise.join(', ')}
                        </div>
                      </div>
                      {selectedExpert === expert.id && (
                        <div className="w-5 h-5 rounded-full bg-neon-500 flex items-center justify-center">
                          <div className="w-2 h-2 rounded-full bg-white" />
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Question */}
            <div>
              <label className="block text-sm font-medium text-void-300 mb-2">
                Your question:
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask your question..."
                className="w-full px-4 py-3 bg-void-800 border border-void-700 rounded-lg
                         text-white placeholder-void-500 resize-none
                         focus:border-neon-500 focus:ring-1 focus:ring-neon-500
                         selection:bg-neon-500/30 selection:text-white"
                rows={4}
                style={{ color: '#ffffff' }}
              />
              <p className="text-xs text-void-500 mt-1">
                Auto-filled from prediction - edit if needed
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-void-800 flex items-center justify-between">
            <p className="text-xs text-void-500">
              This is a quick ping, not a formal review request
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-void-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSend}
                disabled={!selectedExpert || !question.trim() || askMutation.isPending}
                className="flex items-center gap-2 px-6 py-2 bg-neon-500 text-white font-medium
                         rounded-lg hover:bg-neon-600 disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all"
              >
                <Send className="w-4 h-4" />
                {askMutation.isPending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
