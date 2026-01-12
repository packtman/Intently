import type {
  Review,
  ReviewStatus,
  DashboardData,
  CollaborationFeatures,
  FindingValidation,
  FindingComment,
  FindingAssignment,
  ExpertFeedback,
  ValidateFindingRequest,
  AddCommentRequest,
  AssignFindingRequest,
  ValidationStats,
  // Phase 5 types
  ReviewLifecycle,
  LifecycleHistoryEntry,
  UpdateLifecycleRequest,
  ReviewRequest,
  CreateReviewRequestRequest,
  RespondToRequestRequest,
  ConsensusStatus,
  AddConsensusVoteRequest,
  ConsensusVoteData,
  LearnedPattern,
  PatternInsights,
  // PM-focused types
  PRDChangesResponse,
  PRDChange,
  PRDQualityScore,
  EffortEstimation,
  ExpertAskRequest,
  ExpertResponseRequest,
  PMPreferences,
  // Side-by-side diff types
  SideBySideDiff,
  PRDFileInfo,
  SavePRDResult,
} from '../types'

class ApiService {
  private baseUrl: string = ''

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Reviews
  async listReviews(): Promise<Review[]> {
    return this.fetch<Review[]>('/api/reviews')
  }

  async getReviewStatus(reviewId: string): Promise<ReviewStatus> {
    return this.fetch<ReviewStatus>(`/api/reviews/${reviewId}/status`)
  }

  async getReviewDashboard(reviewId: string): Promise<DashboardData> {
    return this.fetch<DashboardData>(`/api/reviews/${reviewId}/dashboard`)
  }

  // ==================== Collaboration Features ====================
  // These methods support the team collaboration workflow

  // Feature Flags
  async getCollaborationFeatures(): Promise<CollaborationFeatures> {
    return this.fetch<CollaborationFeatures>('/api/collaboration/features')
  }

  // Finding Validation
  async validateFinding(
    reviewId: string,
    findingId: string,
    request: ValidateFindingRequest
  ): Promise<FindingValidation & { message: string }> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/validate`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getFindingValidation(
    reviewId: string,
    findingId: string
  ): Promise<FindingValidation | { status: 'pending'; validated: false }> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/validation`)
  }

  async getReviewValidations(
    reviewId: string
  ): Promise<{ review_id: string; validations: Record<string, FindingValidation>; stats: ValidationStats }> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/validations`)
  }

  // Comments
  async addComment(
    reviewId: string,
    findingId: string,
    request: AddCommentRequest
  ): Promise<FindingComment> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/comments`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getComments(reviewId: string, findingId: string): Promise<FindingComment[]> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/comments`)
  }

  // Team Assignment
  async assignFinding(
    reviewId: string,
    findingId: string,
    request: AssignFindingRequest
  ): Promise<FindingAssignment> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/assign`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getReviewAssignments(
    reviewId: string
  ): Promise<{ review_id: string; assignments: Record<string, FindingAssignment>; by_team: Record<string, string[]> }> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/assignments`)
  }

  // Expert Feedback
  async submitExpertFeedback(
    reviewId: string,
    findingId: string,
    request: {
      feedback_type: 'accuracy' | 'severity' | 'recommendation' | 'context'
      original_value: string
      expert_value: string
      expert_id: string
      expert_team: string
      reasoning: string
    }
  ): Promise<ExpertFeedback> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getFindingFeedback(reviewId: string, findingId: string): Promise<ExpertFeedback[]> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/feedback`)
  }

  // ==================== Phase 5: Review Lifecycle ====================

  async updateReviewLifecycle(
    reviewId: string,
    request: UpdateLifecycleRequest
  ): Promise<ReviewLifecycle> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/lifecycle`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getReviewLifecycle(reviewId: string): Promise<ReviewLifecycle> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/lifecycle`)
  }

  async getLifecycleHistory(reviewId: string): Promise<LifecycleHistoryEntry[]> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/lifecycle/history`)
  }

  // ==================== Phase 5: Cross-Team Requests ====================

  async createReviewRequest(
    reviewId: string,
    request: CreateReviewRequestRequest
  ): Promise<ReviewRequest> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/requests`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getReviewRequests(reviewId: string): Promise<ReviewRequest[]> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/requests`)
  }

  async getTeamRequests(team: string): Promise<ReviewRequest[]> {
    return this.fetch(`/api/collaboration/teams/${team}/requests`)
  }

  async respondToRequest(
    requestId: string,
    request: RespondToRequestRequest
  ): Promise<ReviewRequest> {
    return this.fetch(`/api/collaboration/requests/${requestId}/respond`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // ==================== Phase 5: Consensus Mode ====================

  async addConsensusVote(
    reviewId: string,
    findingId: string,
    request: AddConsensusVoteRequest
  ): Promise<ConsensusVoteData> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/consensus`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getConsensusStatus(reviewId: string, findingId: string): Promise<ConsensusStatus> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/findings/${findingId}/consensus`)
  }

  // ==================== Phase 5: Pattern Learning ====================

  async getSimilarPatterns(patternType: string, patternSignature: string): Promise<LearnedPattern[]> {
    return this.fetch(
      `/api/collaboration/patterns/similar?pattern_type=${encodeURIComponent(patternType)}&pattern_signature=${encodeURIComponent(patternSignature)}`
    )
  }

  async getPatternInsights(): Promise<PatternInsights> {
    return this.fetch('/api/collaboration/patterns/insights')
  }

  async getFeedbackStats(): Promise<{
    total_feedback: number
    by_type: Record<string, number>
    by_team: Record<string, number>
    common_rejection_reasons: Record<string, number>
  }> {
    return this.fetch('/api/collaboration/feedback/stats')
  }

  // ==================== PM-Focused Features ====================

  // PRD Changes
  async getPRDChanges(reviewId: string): Promise<PRDChangesResponse> {
    return this.fetch(`/api/reviews/${reviewId}/changes`)
  }

  async acceptPRDChange(
    reviewId: string,
    changeId: string,
    editedText?: string
  ): Promise<{ applied: boolean; updated_prd: string; change_summary: string }> {
    return this.fetch(`/api/reviews/${reviewId}/changes/${changeId}/accept`, {
      method: 'POST',
      body: JSON.stringify({ edited_text: editedText || null }),
    })
  }

  async rejectPRDChange(reviewId: string, changeId: string): Promise<{ rejected: boolean }> {
    return this.fetch(`/api/reviews/${reviewId}/changes/${changeId}/reject`, {
      method: 'POST',
    })
  }

  async bulkAcceptChanges(
    reviewId: string,
    changeIds?: string[],
    filter?: { teams?: string[]; severities?: string[] }
  ): Promise<{
    applied: number
    skipped: number
    updated_prd: string
    changes_applied: Array<{ id: string; summary: string }>
  }> {
    return this.fetch(`/api/reviews/${reviewId}/changes/bulk-accept`, {
      method: 'POST',
      body: JSON.stringify({
        change_ids: changeIds || null,
        filter: filter || null,
      }),
    })
  }

  async undoLastChange(reviewId: string): Promise<{ reverted: boolean; restored_prd: string }> {
    return this.fetch(`/api/reviews/${reviewId}/changes/undo`, {
      method: 'POST',
    })
  }

  // PRD Quality & Effort
  async getPRDQuality(reviewId: string): Promise<PRDQualityScore> {
    return this.fetch(`/api/reviews/${reviewId}/quality`)
  }

  async getEffortEstimation(reviewId: string): Promise<EffortEstimation> {
    return this.fetch(`/api/reviews/${reviewId}/estimate`)
  }

  // PRD Download & Re-analysis
  async downloadPRD(reviewId: string): Promise<{ content: string; filename: string; content_type: string }> {
    return this.fetch(`/api/reviews/${reviewId}/prd/download`)
  }

  async reAnalyzePRD(reviewId: string): Promise<{
    re_analyzed: boolean
    new_predictions_count: number
    updated_quality_score: number | null
  }> {
    return this.fetch(`/api/reviews/${reviewId}/re-analyze`, {
      method: 'POST',
    })
  }

  // Expert Assist
  async askExpert(request: ExpertAskRequest): Promise<{ ask_id: string }> {
    return this.fetch('/api/expert-assist/ask', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async respondToExpertAsk(askId: string, request: ExpertResponseRequest): Promise<{ responded: boolean }> {
    return this.fetch(`/api/expert-assist/respond/${askId}`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // PM Preferences
  async getPMPreferences(userId: string = 'default'): Promise<PMPreferences> {
    return this.fetch(`/api/preferences?user_id=${userId}`)
  }

  async updatePMPreferences(userId: string, preferences: Partial<PMPreferences>): Promise<PMPreferences> {
    return this.fetch(`/api/preferences?user_id=${userId}`, {
      method: 'PUT',
      body: JSON.stringify(preferences),
    })
  }

  async mutePattern(userId: string, patternDescription: string): Promise<{ learned: boolean; pattern_id: string }> {
    return this.fetch(`/api/preferences/mute?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ pattern_description: patternDescription }),
    })
  }

  async unmutePattern(userId: string, patternId: string): Promise<{ unmuted: boolean }> {
    return this.fetch(`/api/preferences/mute/${patternId}?user_id=${userId}`, {
      method: 'DELETE',
    })
  }

  // Pattern Learning
  async getPatternInsights(): Promise<PatternInsights> {
    return this.fetch('/api/patterns/insights')
  }

  // ==================== Side-by-Side Diff & File Save ====================

  /**
   * Get side-by-side diff for a specific PRD change.
   * Returns aligned original and suggested lines with word-level highlighting.
   */
  async getSideBySideDiff(reviewId: string, changeId: string): Promise<SideBySideDiff> {
    return this.fetch(`/api/reviews/${reviewId}/changes/${changeId}/side-by-side`)
  }

  /**
   * Get the file path info for a PRD.
   */
  async getPRDFileInfo(reviewId: string): Promise<PRDFileInfo> {
    return this.fetch(`/api/reviews/${reviewId}/prd/file-info`)
  }

  /**
   * Save the current PRD (with accepted changes) back to the original file.
   * Creates a backup before overwriting.
   */
  async savePRDToFile(reviewId: string): Promise<SavePRDResult> {
    return this.fetch(`/api/reviews/${reviewId}/prd/save-to-file`, {
      method: 'POST',
    })
  }
}

export const api = new ApiService()

