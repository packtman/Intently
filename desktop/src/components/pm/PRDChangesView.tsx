/**
 * PRD Changes View - Main view for displaying and managing PRD changes
 * 
 * Shows all predicted questions with diff-style PRD changes
 */

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  Filter,
  Download,
  RotateCcw,
  RefreshCw,
  Layers,
  Save,
  FileText,
} from 'lucide-react'
import { PRDChangeCard } from './PRDChangeCard'
import { BulkAcceptPanel } from './BulkAcceptPanel'
import { SideBySideDiffModal } from './SideBySideDiffModal'
import { api } from '../../services/api'
import type { PRDChange, CollaborationFeatures } from '../../types'

interface PRDChangesViewProps {
  reviewId: string
  onAskExpert?: (predictionId: string, question: string) => void
}

export function PRDChangesView({ reviewId, onAskExpert }: PRDChangesViewProps) {
  const queryClient = useQueryClient()
  const [showBulkAccept, setShowBulkAccept] = useState(false)
  const [selectedChanges, setSelectedChanges] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<{ teams?: string[]; severities?: string[] }>({})
  const [selectedChangeForDiff, setSelectedChangeForDiff] = useState<PRDChange | null>(null)
  const [showSaveSuccess, setShowSaveSuccess] = useState(false)

  // Fetch PRD changes
  const { data: changesData, isLoading } = useQuery({
    queryKey: ['prd-changes', reviewId],
    queryFn: () => api.getPRDChanges(reviewId),
    enabled: !!reviewId,
  })

  // Accept mutation
  const acceptMutation = useMutation({
    mutationFn: ({ changeId, editedText }: { changeId: string; editedText?: string }) =>
      api.acceptPRDChange(reviewId, changeId, editedText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prd-changes', reviewId] })
      queryClient.invalidateQueries({ queryKey: ['review-dashboard', reviewId] })
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: (changeId: string) => api.rejectPRDChange(reviewId, changeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prd-changes', reviewId] })
    },
  })

  // Undo mutation
  const undoMutation = useMutation({
    mutationFn: () => api.undoLastChange(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prd-changes', reviewId] })
    },
  })

  // Download mutation
  const downloadMutation = useMutation({
    mutationFn: () => api.downloadPRD(reviewId),
    onSuccess: (data) => {
      // Create download link
      const blob = new Blob([data.content], { type: data.content_type })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = data.filename
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  // Re-analyze mutation
  const reAnalyzeMutation = useMutation({
    mutationFn: () => api.reAnalyzePRD(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prd-changes', reviewId] })
      queryClient.invalidateQueries({ queryKey: ['review-dashboard', reviewId] })
    },
  })

  // Check feature flags
  const { data: features } = useQuery<CollaborationFeatures>({
    queryKey: ['collaboration-features'],
    queryFn: () => api.getCollaborationFeatures(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })
  
  const saveToFileEnabled = features?.prd_save_to_file ?? false
  const sideBySideDiffEnabled = features?.side_by_side_diff ?? false

  // Check if file path is set (for save-to-file button) - only query if feature is enabled
  const { data: fileInfo } = useQuery({
    queryKey: ['prd-file-info', reviewId],
    queryFn: () => api.getPRDFileInfo(reviewId),
    enabled: !!reviewId && saveToFileEnabled,
  })

  // Save to file mutation
  const saveMutation = useMutation({
    mutationFn: () => api.savePRDToFile(reviewId),
    onSuccess: () => {
      setShowSaveSuccess(true)
      setTimeout(() => setShowSaveSuccess(false), 3000)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-surface-400">Loading PRD changes...</div>
      </div>
    )
  }

  if (!changesData || changesData.changes.length === 0) {
    return (
      <div className="p-8 text-center">
        <Layers className="w-12 h-12 text-surface-600 mx-auto mb-4" />
        <p className="text-surface-400">No PRD changes suggested</p>
        <p className="text-sm text-surface-500 mt-2">Your PRD looks complete!</p>
      </div>
    )
  }

  // Filter changes
  const filteredChanges = changesData.changes.filter((change) => {
    if (filter.teams && !filter.teams.includes(change.team)) return false
    if (filter.severities && !filter.severities.includes(change.severity)) return false
    return true
  })

  const openChanges = filteredChanges.filter((c) => c.status === 'open')
  const acceptedChanges = filteredChanges.filter((c) => c.status === 'accepted')
  const rejectedChanges = filteredChanges.filter((c) => c.status === 'rejected')

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">PRD Changes</h2>
          <p className="text-surface-400 mt-1">
            {openChanges.length} open changes • {acceptedChanges.length} accepted • {rejectedChanges.length} rejected
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* File info indicator - only shown if save-to-file feature is enabled */}
          {saveToFileEnabled && fileInfo?.has_file_path && (
            <div className="flex items-center gap-1.5 text-sm text-surface-400 mr-2">
              <FileText className="w-4 h-4" />
              <span>{fileInfo.file_name}</span>
            </div>
          )}
          
          {/* Save success message */}
          {showSaveSuccess && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex items-center gap-2 text-green-400 text-sm mr-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Saved!</span>
            </motion.div>
          )}

          <button
            onClick={() => setShowBulkAccept(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500/20 border border-primary-500/50
                     text-primary-400 font-medium rounded-lg hover:bg-primary-500/30 transition-all"
          >
            <CheckCircle2 className="w-4 h-4" />
            Bulk Accept
          </button>
          <button
            onClick={() => undoMutation.mutate()}
            disabled={undoMutation.isPending || acceptedChanges.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-surface-800 border border-surface-700
                     text-surface-300 font-medium rounded-lg hover:bg-surface-700
                     disabled:opacity-50 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            Undo
          </button>
          <button
            onClick={() => downloadMutation.mutate()}
            disabled={downloadMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-surface-800 border border-surface-700
                     text-surface-300 font-medium rounded-lg hover:bg-surface-700
                     disabled:opacity-50 transition-all"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
          {/* Save to File button - only shown if feature is enabled and file path is set */}
          {saveToFileEnabled && fileInfo?.has_file_path && (
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || acceptedChanges.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-500/50
                       text-green-400 font-medium rounded-lg hover:bg-green-500/30
                       disabled:opacity-50 transition-all"
            >
              <Save className={`w-4 h-4 ${saveMutation.isPending ? 'animate-pulse' : ''}`} />
              Save to File
            </button>
          )}
          <button
            onClick={() => reAnalyzeMutation.mutate()}
            disabled={reAnalyzeMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-surface-800 border border-surface-700
                     text-surface-300 font-medium rounded-lg hover:bg-surface-700
                     disabled:opacity-50 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${reAnalyzeMutation.isPending ? 'animate-spin' : ''}`} />
            Re-analyze
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      {changesData.summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-surface-900/50 rounded-lg border border-surface-800 p-4">
            <div className="text-2xl font-bold text-white">{changesData.summary.total}</div>
            <div className="text-sm text-surface-400">Total Changes</div>
          </div>
          <div className="bg-surface-900/50 rounded-lg border border-surface-800 p-4">
            <div className="text-2xl font-bold text-red-400">{changesData.summary.by_severity.blocker || 0}</div>
            <div className="text-sm text-surface-400">Blockers</div>
          </div>
          <div className="bg-surface-900/50 rounded-lg border border-surface-800 p-4">
            <div className="text-2xl font-bold text-amber-400">{changesData.summary.by_severity.likely || 0}</div>
            <div className="text-sm text-surface-400">Likely</div>
          </div>
          <div className="bg-surface-900/50 rounded-lg border border-surface-800 p-4">
            <div className="text-2xl font-bold text-blue-400">{changesData.summary.by_severity.possible || 0}</div>
            <div className="text-sm text-surface-400">Possible</div>
          </div>
        </div>
      )}

      {/* Changes List */}
      <div className="space-y-4">
        {openChanges.map((change, index) => (
          <PRDChangeCard
            key={change.id}
            change={change}
            index={index + 1}
            total={openChanges.length}
            onAccept={(changeId, editedText) => acceptMutation.mutate({ changeId, editedText })}
            onReject={(changeId) => rejectMutation.mutate(changeId)}
            onViewDiff={sideBySideDiffEnabled ? (change) => setSelectedChangeForDiff(change) : undefined}
            onAskExpert={onAskExpert ? (changeId) => {
              const change = openChanges.find(c => c.id === changeId)
              if (change) {
                onAskExpert(changeId, change.reasoning)
              }
            } : undefined}
            isAccepting={acceptMutation.isPending}
            isRejecting={rejectMutation.isPending}
          />
        ))}
      </div>

      {/* Bulk Accept Panel */}
      {showBulkAccept && (
        <BulkAcceptPanel
          changes={openChanges}
          summary={changesData.summary}
          onClose={() => setShowBulkAccept(false)}
          onBulkAccept={(changeIds, filter) => {
            api.bulkAcceptChanges(reviewId, changeIds, filter).then(() => {
              queryClient.invalidateQueries({ queryKey: ['prd-changes', reviewId] })
              setShowBulkAccept(false)
            })
          }}
        />
      )}

      {/* Side-by-Side Diff Modal - only rendered if feature is enabled */}
      {sideBySideDiffEnabled && selectedChangeForDiff && (
        <SideBySideDiffModal
          isOpen={!!selectedChangeForDiff}
          onClose={() => setSelectedChangeForDiff(null)}
          reviewId={reviewId}
          change={selectedChangeForDiff}
          onAccept={(changeId, editedText) => {
            acceptMutation.mutate({ changeId, editedText })
            setSelectedChangeForDiff(null)
          }}
          onReject={(changeId) => {
            rejectMutation.mutate(changeId)
            setSelectedChangeForDiff(null)
          }}
          isAccepting={acceptMutation.isPending}
          isRejecting={rejectMutation.isPending}
        />
      )}
    </div>
  )
}
