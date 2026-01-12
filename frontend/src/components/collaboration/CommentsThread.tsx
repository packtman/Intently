/**
 * CommentsThread - Threaded discussion component for findings
 *
 * Enables team members to discuss findings asynchronously with threaded replies.
 * Feature flag: FEATURE_COMMENTS=true
 */

import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare,
  Send,
  Reply,
  MoreVertical,
  Trash2,
  User,
  Building2,
  Clock,
  Loader2,
  ChevronDown,
} from 'lucide-react'
import { api } from '../../services/api'
import type { Finding, FindingComment, AddCommentRequest } from '../../types'

interface CommentsThreadProps {
  finding: Finding
  reviewId: string
  enabled: boolean
  currentUserId?: string
  currentUserName?: string
  currentTeam?: string
}

export function CommentsThread({
  finding,
  reviewId,
  enabled,
  currentUserId = 'user-1',
  currentUserName = 'Current User',
  currentTeam = 'security',
}: CommentsThreadProps) {
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(false)
  const [newComment, setNewComment] = useState('')
  const [replyingTo, setReplyingTo] = useState<string | null>(null)
  const [replyContent, setReplyContent] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const replyTextareaRef = useRef<HTMLTextAreaElement>(null)

  // Don't render if feature is disabled
  if (!enabled) return null

  // Fetch comments for this finding
  const { data: comments = [], isLoading } = useQuery({
    queryKey: ['finding-comments', reviewId, finding.id],
    queryFn: () => api.getComments(reviewId, finding.id),
    enabled: enabled && isExpanded,
  })

  // Add comment mutation
  const addCommentMutation = useMutation({
    mutationFn: (request: AddCommentRequest) =>
      api.addComment(reviewId, finding.id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding-comments', reviewId, finding.id] })
      setNewComment('')
      setReplyingTo(null)
      setReplyContent('')
    },
  })

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [newComment])

  useEffect(() => {
    if (replyTextareaRef.current) {
      replyTextareaRef.current.style.height = 'auto'
      replyTextareaRef.current.style.height = `${replyTextareaRef.current.scrollHeight}px`
    }
  }, [replyContent])

  const handleSubmitComment = () => {
    if (!newComment.trim()) return

    addCommentMutation.mutate({
      content: newComment.trim(),
      author_id: currentUserId,
      author_name: currentUserName,
      author_team: currentTeam,
    })
  }

  const handleSubmitReply = (parentId: string) => {
    if (!replyContent.trim()) return

    addCommentMutation.mutate({
      content: replyContent.trim(),
      author_id: currentUserId,
      author_name: currentUserName,
      author_team: currentTeam,
      parent_comment_id: parentId,
    })
  }

  // Organize comments into threads
  const rootComments = comments.filter(c => !c.parent_comment_id)
  const getReplies = (commentId: string) => 
    comments.filter(c => c.parent_comment_id === commentId)

  const commentCount = comments.length

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 rounded-xl border border-surface-700 bg-surface-800/30 overflow-hidden"
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-surface-700 flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-surface-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium text-white">
              Discussion
              {commentCount > 0 && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-xs">
                  {commentCount}
                </span>
              )}
            </p>
            <p className="text-xs text-surface-400">
              {commentCount === 0
                ? 'Start a conversation about this finding'
                : `${commentCount} comment${commentCount !== 1 ? 's' : ''}`}
            </p>
          </div>
        </div>
        <ChevronDown
          className={`w-5 h-5 text-surface-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 pt-0 space-y-4 border-t border-surface-700">
              {/* Loading state */}
              {isLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 text-surface-400 animate-spin" />
                </div>
              )}

              {/* Comments list */}
              {!isLoading && rootComments.length > 0 && (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {rootComments.map((comment) => (
                    <CommentItem
                      key={comment.id}
                      comment={comment}
                      replies={getReplies(comment.id)}
                      getReplies={getReplies}
                      onReply={(id) => {
                        setReplyingTo(id)
                        setReplyContent('')
                      }}
                      replyingTo={replyingTo}
                      replyContent={replyContent}
                      onReplyContentChange={setReplyContent}
                      onSubmitReply={handleSubmitReply}
                      onCancelReply={() => setReplyingTo(null)}
                      isSubmitting={addCommentMutation.isPending}
                      replyTextareaRef={replyTextareaRef}
                      currentUserId={currentUserId}
                    />
                  ))}
                </div>
              )}

              {/* Empty state */}
              {!isLoading && rootComments.length === 0 && (
                <div className="text-center py-6">
                  <MessageSquare className="w-10 h-10 text-surface-600 mx-auto mb-2" />
                  <p className="text-surface-400 text-sm">No comments yet</p>
                  <p className="text-surface-500 text-xs">Be the first to start the discussion</p>
                </div>
              )}

              {/* New comment input */}
              <div className="pt-4 border-t border-surface-700">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-primary-400" />
                  </div>
                  <div className="flex-1">
                    <textarea
                      ref={textareaRef}
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      placeholder="Add a comment..."
                      className="w-full p-3 rounded-lg bg-surface-800 border border-surface-700 text-white text-sm placeholder:text-surface-500 resize-none focus:outline-none focus:border-primary-500/50 min-h-[44px] max-h-32"
                      rows={1}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                          handleSubmitComment()
                        }
                      }}
                    />
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center gap-2 text-xs text-surface-500">
                        <Building2 className="w-3 h-3" />
                        <span>{currentTeam} team</span>
                      </div>
                      <button
                        onClick={handleSubmitComment}
                        disabled={!newComment.trim() || addCommentMutation.isPending}
                        className={`
                          flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                          ${
                            newComment.trim()
                              ? 'bg-primary-500 text-white hover:bg-primary-400'
                              : 'bg-surface-700 text-surface-500 cursor-not-allowed'
                          }
                        `}
                      >
                        {addCommentMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                        Comment
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Error message */}
              {addCommentMutation.error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                  <p className="text-sm text-red-400">
                    {addCommentMutation.error instanceof Error
                      ? addCommentMutation.error.message
                      : 'Failed to add comment'}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

interface CommentItemProps {
  comment: FindingComment
  replies: FindingComment[]
  getReplies: (commentId: string) => FindingComment[]
  onReply: (commentId: string) => void
  replyingTo: string | null
  replyContent: string
  onReplyContentChange: (content: string) => void
  onSubmitReply: (parentId: string) => void
  onCancelReply: () => void
  isSubmitting: boolean
  replyTextareaRef: React.RefObject<HTMLTextAreaElement>
  currentUserId: string
  depth?: number
}

function CommentItem({
  comment,
  replies,
  getReplies,
  onReply,
  replyingTo,
  replyContent,
  onReplyContentChange,
  onSubmitReply,
  onCancelReply,
  isSubmitting,
  replyTextareaRef,
  currentUserId,
  depth = 0,
}: CommentItemProps) {
  const [showActions, setShowActions] = useState(false)
  const isOwn = comment.author_id === currentUserId
  const maxDepth = 3 // Limit nesting depth

  const teamColors: Record<string, string> = {
    security: 'bg-cyan-500/20 text-cyan-400',
    privacy: 'bg-purple-500/20 text-purple-400',
    compliance: 'bg-amber-500/20 text-amber-400',
    engineering: 'bg-green-500/20 text-green-400',
    architecture: 'bg-orange-500/20 text-orange-400',
  }

  const teamColor = teamColors[comment.author_team] || 'bg-surface-700 text-surface-400'

  return (
    <div className={`${depth > 0 ? 'ml-8 pl-4 border-l-2 border-surface-700' : ''}`}>
      <div
        className="group relative"
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
      >
        <div className="flex items-start gap-3">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${teamColor}`}>
            <span className="text-xs font-medium">{comment.author_name.charAt(0).toUpperCase()}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-white">{comment.author_name}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs ${teamColor}`}>
                {comment.author_team}
              </span>
              <span className="text-xs text-surface-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatRelativeTime(comment.created_at)}
              </span>
            </div>
            <p className="text-sm text-surface-300 mt-1 whitespace-pre-wrap break-words">
              {comment.content}
            </p>

            {/* Reply button */}
            {depth < maxDepth && (
              <button
                onClick={() => onReply(comment.id)}
                className="flex items-center gap-1 mt-2 text-xs text-surface-500 hover:text-primary-400 transition-colors"
              >
                <Reply className="w-3 h-3" />
                Reply
              </button>
            )}
          </div>

          {/* Actions menu (for own comments) */}
          {isOwn && showActions && (
            <div className="absolute top-0 right-0">
              <button className="p-1 rounded hover:bg-surface-700 text-surface-500 hover:text-white transition-colors">
                <MoreVertical className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Reply input */}
        {replyingTo === comment.id && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-3 ml-11"
          >
            <textarea
              ref={replyTextareaRef}
              value={replyContent}
              onChange={(e) => onReplyContentChange(e.target.value)}
              placeholder={`Reply to ${comment.author_name}...`}
              className="w-full p-3 rounded-lg bg-surface-800 border border-surface-700 text-white text-sm placeholder:text-surface-500 resize-none focus:outline-none focus:border-primary-500/50 min-h-[44px]"
              rows={2}
              autoFocus
            />
            <div className="flex items-center justify-end gap-2 mt-2">
              <button
                onClick={onCancelReply}
                className="px-3 py-1.5 text-sm text-surface-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => onSubmitReply(comment.id)}
                disabled={!replyContent.trim() || isSubmitting}
                className={`
                  flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                  ${
                    replyContent.trim()
                      ? 'bg-primary-500 text-white hover:bg-primary-400'
                      : 'bg-surface-700 text-surface-500 cursor-not-allowed'
                  }
                `}
              >
                {isSubmitting ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Reply className="w-3 h-3" />
                )}
                Reply
              </button>
            </div>
          </motion.div>
        )}
      </div>

      {/* Nested replies */}
      {replies.length > 0 && (
        <div className="mt-3 space-y-3">
          {replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              replies={getReplies(reply.id)}
              getReplies={getReplies}
              onReply={onReply}
              replyingTo={replyingTo}
              replyContent={replyContent}
              onReplyContentChange={onReplyContentChange}
              onSubmitReply={onSubmitReply}
              onCancelReply={onCancelReply}
              isSubmitting={isSubmitting}
              replyTextareaRef={replyTextareaRef}
              currentUserId={currentUserId}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * CommentCountBadge - Compact badge showing comment count
 */
export function CommentCountBadge({ count }: { count: number }) {
  if (count === 0) return null

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-700 text-surface-400 text-xs">
      <MessageSquare className="w-3 h-3" />
      {count}
    </span>
  )
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}

