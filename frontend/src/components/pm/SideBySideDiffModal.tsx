/**
 * SideBySideDiffModal - Modal component for viewing PRD changes side-by-side
 * 
 * Shows:
 * - Original PRD content (left pane) vs Suggested changes (right pane)
 * - Line numbers and status indicators
 * - Word-level change highlighting
 * - Accept/Reject/Edit actions
 * - Save to file option
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  X,
  CheckCircle2,
  Loader2,
} from 'lucide-react'
import { DiffLine } from './DiffLine'
import { api } from '../../services/api'
import type { PRDChange, SideBySideDiff } from '../../types'

interface SideBySideDiffModalProps {
  isOpen: boolean
  onClose: () => void
  reviewId: string
  change: PRDChange
  onAccept: (changeId: string, editedText?: string) => void
  onReject: (changeId: string) => void
  isAccepting?: boolean
  isRejecting?: boolean
}

export function SideBySideDiffModal({
  isOpen,
  onClose,
  reviewId,
  change,
  onAccept,
  onReject,
  isAccepting = false,
  isRejecting = false,
}: SideBySideDiffModalProps) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [editedText, setEditedText] = useState(change.suggested_text)
  const [showSuccess, setShowSuccess] = useState(false)

  // Fetch side-by-side diff data
  const { data: diffData, isLoading: isDiffLoading } = useQuery({
    queryKey: ['side-by-side-diff', reviewId, change.id],
    queryFn: () => api.getSideBySideDiff(reviewId, change.id),
    enabled: isOpen && !!reviewId && !!change.id,
  })

  // Check if file path is set
  const { data: fileInfo } = useQuery({
    queryKey: ['prd-file-info', reviewId],
    queryFn: () => api.getPRDFileInfo(reviewId),
    enabled: isOpen && !!reviewId,
  })

  // Save to file mutation
  const saveMutation = useMutation({
    mutationFn: () => api.savePRDToFile(reviewId),
    onSuccess: () => {
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 3000)
    },
  })

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setEditedText(change.suggested_text)
      setIsEditing(false)
      setShowSuccess(false)
    }
  }, [isOpen, change.suggested_text])

  const handleAccept = () => {
    if (isEditing) {
      onAccept(change.id, editedText)
    } else {
      onAccept(change.id)
    }
  }

  const handleAcceptAndSave = async () => {
    // First accept the change
    if (isEditing) {
      onAccept(change.id, editedText)
    } else {
      onAccept(change.id)
    }
    
    // Then save to file if path is set
    if (fileInfo?.has_file_path) {
      // Wait a moment for the accept to process
      setTimeout(() => {
        saveMutation.mutate()
      }, 500)
    }
  }

  const severityColors = {
    blocker: 'bg-red-500/20 border-red-500/50 text-red-400',
    likely: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
    possible: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-[95vw] max-w-7xl max-h-[90vh] bg-surface-900 rounded-2xl 
                     border border-surface-700 shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header - matching mockup diff-header styling */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-surface-700 bg-surface-800">
            <div className="flex items-center gap-4">
              {/* File info with icon */}
              <div className="flex items-center gap-3">
                <span className="text-xl">📝</span>
                <div>
                  <div className="font-mono text-sm text-white">
                    {diffData?.file_name || 'PRD.md'}
                  </div>
                  <div className="text-xs text-surface-500">
                    PRD Changes • Section: {change.section}
                  </div>
                </div>
              </div>
              
              {/* Stats */}
              {diffData?.stats && (
                <div className="flex items-center gap-4 font-mono text-sm ml-4">
                  <span className="text-red-400">−{diffData.stats.lines_removed} lines</span>
                  <span className="text-emerald-400">+{diffData.stats.lines_added} lines</span>
                </div>
              )}
              
              {/* Severity badge */}
              <span className={`px-2 py-1 rounded text-xs font-semibold uppercase ${severityColors[change.severity]}`}>
                {change.severity}
              </span>
            </div>
            
            {/* Action buttons - matching mockup btn styling */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => onReject(change.id)}
                disabled={isRejecting || isAccepting}
                className="flex items-center gap-1.5 px-4 py-2 bg-surface-800 border border-surface-600
                         text-surface-300 text-sm font-medium rounded-lg hover:bg-surface-700 hover:text-white
                         disabled:opacity-50 transition-all"
              >
                <span>✕</span>
                Reject
              </button>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-500 text-white
                         text-sm font-medium rounded-lg hover:bg-blue-600 transition-all"
              >
                <span>✎</span>
                {isEditing ? 'Cancel Edit' : 'Edit'}
              </button>
              <button
                onClick={handleAccept}
                disabled={isAccepting || isRejecting}
                className="flex items-center gap-1.5 px-5 py-2 bg-emerald-500 text-white
                         text-sm font-medium rounded-lg hover:bg-emerald-600 hover:-translate-y-0.5
                         disabled:opacity-50 transition-all"
              >
                {isAccepting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <span>✓</span>
                )}
                Accept Changes
              </button>
              <button
                onClick={onClose}
                className="p-2 text-surface-400 hover:text-white transition-colors ml-2"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content - Split panes matching mockup */}
          <div className="flex-1 overflow-hidden grid grid-cols-2">
            {isDiffLoading ? (
              <div className="col-span-2 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
              </div>
            ) : (
              <>
                {/* Original Pane */}
                <div className="flex flex-col border-r border-surface-700">
                  {/* Pane header - matching mockup pane-header styling */}
                  <div className="px-4 py-3 bg-surface-800 border-b border-surface-700 flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-red-400">
                      ← Original PRD
                    </span>
                    <span className="text-[0.65rem] font-semibold uppercase px-2 py-1 bg-red-500/15 text-red-400 rounded">
                      Current Version
                    </span>
                  </div>
                  {/* Pane content */}
                  <div className="flex-1 overflow-auto bg-surface-900 font-mono text-[0.85rem] leading-[1.7]">
                    {diffData?.original_lines.map((line, index) => (
                      <DiffLine key={index} line={line} side="original" />
                    ))}
                  </div>
                </div>

                {/* Suggested Pane */}
                <div className="flex flex-col">
                  {/* Pane header */}
                  <div className="px-4 py-3 bg-surface-800 border-b border-surface-700 flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                      Suggested Changes →
                    </span>
                    <span className="text-[0.65rem] font-semibold uppercase px-2 py-1 bg-emerald-500/15 text-emerald-400 rounded">
                      AI Suggestion
                    </span>
                  </div>
                  {/* Pane content */}
                  <div className="flex-1 overflow-auto bg-surface-900 font-mono text-[0.85rem] leading-[1.7]">
                    {isEditing ? (
                      <div className="p-4">
                        <textarea
                          value={editedText}
                          onChange={(e) => setEditedText(e.target.value)}
                          className="w-full h-full min-h-[400px] px-4 py-3 bg-surface-800 border border-emerald-500/50 
                                   rounded-lg text-white placeholder-surface-500 text-sm font-mono resize-none
                                   focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                          placeholder="Edit the suggested text..."
                        />
                        <p className="text-xs text-surface-500 mt-2">
                          Edit the suggestion before accepting. Your changes will be applied to the PRD.
                        </p>
                      </div>
                    ) : (
                      diffData?.suggested_lines.map((line, index) => (
                        <DiffLine key={index} line={line} side="suggested" />
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Footer - matching mockup diff-footer styling */}
          <div className="px-6 py-4 border-t border-surface-700 bg-surface-800 flex items-center justify-between">
            {/* Change Summary - matching mockup summary styling */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2 text-sm">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="text-surface-400">Lines added:</span>
                <span className="text-white font-semibold">{diffData?.stats.lines_added || 0}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-surface-400">Lines removed:</span>
                <span className="text-white font-semibold">{diffData?.stats.lines_removed || 0}</span>
              </div>
              {(diffData?.stats.lines_modified || 0) > 0 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span className="text-surface-400">Lines modified:</span>
                  <span className="text-white font-semibold">{diffData?.stats.lines_modified}</span>
                </div>
              )}
            </div>

            {/* Action Confirmation Area */}
            <div className="flex items-center gap-4">
              {/* Success Message */}
              {showSuccess && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center gap-2 text-emerald-400 text-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Saved to file!</span>
                </motion.div>
              )}

              {/* File path confirmation text */}
              {fileInfo?.has_file_path && (
                <span className="text-sm text-surface-400">
                  This will update the PRD file on disk
                </span>
              )}

              {/* Confirm & Apply Button - matching mockup */}
              {fileInfo?.has_file_path ? (
                <button
                  onClick={handleAcceptAndSave}
                  disabled={isAccepting || isRejecting || saveMutation.isPending}
                  className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 text-white
                           font-medium rounded-lg hover:bg-emerald-600 hover:-translate-y-0.5
                           disabled:opacity-50 transition-all shadow-lg shadow-emerald-500/25"
                >
                  {saveMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span>✓</span>
                  )}
                  Confirm & Apply
                </button>
              ) : (
                <button
                  onClick={handleAccept}
                  disabled={isAccepting || isRejecting}
                  className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 text-white
                           font-medium rounded-lg hover:bg-emerald-600 hover:-translate-y-0.5
                           disabled:opacity-50 transition-all shadow-lg shadow-emerald-500/25"
                >
                  {isAccepting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span>✓</span>
                  )}
                  Accept & Apply
                </button>
              )}
            </div>
          </div>
          
          {/* Backend Sync Indicator - matching mockup sync-indicator */}
          {fileInfo?.has_file_path && (
            <div className="mx-6 mb-4 mt-2 flex items-center gap-3 px-4 py-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
              <span className="text-purple-400">🔄</span>
              <span className="text-sm text-surface-400">
                <strong className="text-purple-400">Backend Sync:</strong> Accepting will automatically update{' '}
                <code className="bg-purple-500/20 px-1.5 py-0.5 rounded text-purple-300">
                  {fileInfo.file_name}
                </code>{' '}
                in your workspace
              </span>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
