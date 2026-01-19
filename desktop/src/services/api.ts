import type {
  Review,
  ReviewStatus,
  DashboardData,
  ParsedIntent,
  ReviewRequest,
  CollaborationFeatures,
  FindingValidation,
  FindingComment,
  FindingAssignment,
  ExpertFeedback,
  ValidateFindingRequest,
  AddCommentRequest,
  AssignFindingRequest,
  ValidationStats,
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
  // Bulk PRD Analysis types
  BulkAnalysisRequest,
  BulkAnalysisResult,
  BulkAnalysisConfig,
  // PRD Generator types
  PRDGeneratorRequest,
  GeneratedPRD,
  PRDGeneratorStatus,
  PRDGeneratorConfig,
} from '../types'

class ApiService {
  private baseUrl: string = 'http://127.0.0.1:8000'
  private baseUrlCached: boolean = false

  async setBaseUrl(url: string) {
    this.baseUrl = url
    this.baseUrlCached = true
  }

  async getBaseUrl(): Promise<string> {
    // Only fetch from Electron once - cache the result
    if (!this.baseUrlCached && window.electronAPI?.getBackendUrl) {
      this.baseUrl = await window.electronAPI.getBackendUrl()
      this.baseUrlCached = true
    }
    return this.baseUrl
  }

  // Initialize the base URL once on app start
  async init(): Promise<void> {
    await this.getBaseUrl()
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Use cached URL directly - no async IPC call needed
    if (!this.baseUrlCached) await this.getBaseUrl()
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

  async createReview(request: ReviewRequest): Promise<{ review_id: string; status: string; message: string }> {
    return this.fetch('/api/reviews', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getReviewStatus(reviewId: string): Promise<ReviewStatus> {
    return this.fetch<ReviewStatus>(`/api/reviews/${reviewId}/status`)
  }

  async getReviewDashboard(reviewId: string): Promise<DashboardData> {
    return this.fetch<DashboardData>(`/api/reviews/${reviewId}/dashboard`)
  }

  async getReviewMarkdown(reviewId: string): Promise<{ markdown: string }> {
    return this.fetch<{ markdown: string }>(`/api/reviews/${reviewId}/markdown`)
  }

  // PRD Parsing
  async parsePRD(content: string, title?: string): Promise<ParsedIntent> {
    return this.fetch('/api/parse-prd', {
      method: 'POST',
      body: JSON.stringify({
        content,
        source_type: 'markdown',
        title: title || 'PRD Analysis',
      }),
    })
  }

  // Codebase Analysis
  async analyzeCodebase(path: string, languages: string[]): Promise<{
    path: string
    files_analyzed: number
    lines_of_code: number
    api_endpoints: unknown[]
    data_models: unknown[]
    auth_patterns: unknown[]
    existing_controls: string[]
  }> {
    return this.fetch('/api/analyze-codebase', {
      method: 'POST',
      body: JSON.stringify({ path, languages }),
    })
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

  async getCommentCounts(reviewId: string): Promise<Record<string, number>> {
    return this.fetch(`/api/collaboration/reviews/${reviewId}/comment-counts`)
  }

  async deleteComment(commentId: string): Promise<{ deleted: boolean; comment_id: string }> {
    return this.fetch(`/api/collaboration/comments/${commentId}`, {
      method: 'DELETE',
    })
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

  async getTeamQueue(team: string): Promise<FindingAssignment[]> {
    return this.fetch(`/api/collaboration/teams/${team}/queue`)
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
  async getPMPatternInsights(): Promise<{
    total_patterns: number
    by_type: Record<string, number>
    by_decision: Record<string, number>
    most_applied_patterns: Array<{ pattern_signature: string; decision: string; times_applied: number }>
  }> {
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
   * Set the file path for a PRD (for saving back to disk).
   * Should be called after loading a PRD from a file.
   */
  async setPRDFilePath(
    reviewId: string,
    filePath: string,
    fileName?: string
  ): Promise<{ set: boolean; file_path: string; file_name: string }> {
    return this.fetch(`/api/reviews/${reviewId}/prd/set-file-path`, {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath, file_name: fileName || null }),
    })
  }

  /**
   * Get the file path info for a PRD.
   */
  async getPRDFileInfo(reviewId: string): Promise<{
    has_file_path: boolean
    file_path: string | null
    file_name: string | null
    set_at?: string
  }> {
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

  // ==================== Bulk PRD Analysis ====================

  /**
   * Get bulk analysis configuration and status.
   * Check if feature is enabled and get limits/suggestions.
   */
  async getBulkAnalysisConfig(): Promise<BulkAnalysisConfig> {
    return this.fetch('/api/bulk/config')
  }

  /**
   * Analyze multiple PRD files in parallel.
   */
  async analyzeBulkPRDs(request: BulkAnalysisRequest): Promise<BulkAnalysisResult> {
    return this.fetch('/api/bulk/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * Get the result of a bulk PRD analysis by ID.
   */
  async getBulkAnalysisResult(analysisId: string): Promise<BulkAnalysisResult> {
    return this.fetch(`/api/bulk/results/${analysisId}`)
  }

  /**
   * Get codebase suggestions based on usage patterns.
   */
  async getCodebaseSuggestions(): Promise<BulkAnalysisConfig['codebase_suggestions']> {
    return this.fetch('/api/bulk/codebase/suggestions')
  }

  /**
   * Set or clear the default codebase for bulk analysis.
   */
  async setDefaultCodebase(codebasePath: string | null): Promise<{
    set: boolean
    default_codebase_path: string | null
    message: string
  }> {
    return this.fetch('/api/bulk/codebase/default', {
      method: 'POST',
      body: JSON.stringify({ codebase_path: codebasePath }),
    })
  }

  // ==================== PRD Generator ====================

  /**
   * Get PRD Generator configuration and check if feature is enabled.
   */
  async getPRDGeneratorConfig(): Promise<PRDGeneratorConfig> {
    return this.fetch('/api/prd-generator/config')
  }

  /**
   * Start PRD generation from a codebase.
   * Returns a generation ID that can be used to poll status.
   */
  async generatePRD(request: PRDGeneratorRequest): Promise<{ generation_id: string; message: string }> {
    return this.fetch('/api/prd-generator/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * Get the status of a PRD generation job.
   */
  async getPRDGeneratorStatus(generationId: string): Promise<PRDGeneratorStatus> {
    return this.fetch(`/api/prd-generator/${generationId}/status`)
  }

  /**
   * Get the generated PRD result.
   */
  async getGeneratedPRD(generationId: string): Promise<GeneratedPRD> {
    return this.fetch(`/api/prd-generator/${generationId}/result`)
  }

  /**
   * Export the generated PRD in different formats.
   */
  async exportGeneratedPRD(
    generationId: string,
    format: 'markdown' | 'json' | 'html'
  ): Promise<{ content: string; filename: string; content_type: string }> {
    return this.fetch(`/api/prd-generator/${generationId}/export?format=${format}`)
  }

  /**
   * Update a section of the generated PRD.
   */
  async updatePRDSection(
    generationId: string,
    sectionId: string,
    content: string
  ): Promise<{ updated: boolean; section_id: string }> {
    return this.fetch(`/api/prd-generator/${generationId}/sections/${sectionId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    })
  }

  /**
   * Regenerate a specific section of the PRD with more detail or different focus.
   */
  async regeneratePRDSection(
    generationId: string,
    sectionId: string,
    instructions?: string
  ): Promise<{ regenerated: boolean; section: { id: string; title: string; content: string } }> {
    return this.fetch(`/api/prd-generator/${generationId}/sections/${sectionId}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({ instructions: instructions || null }),
    })
  }

  /**
   * List all generated PRDs.
   */
  async listGeneratedPRDs(): Promise<Array<{
    id: string
    title: string
    codebase_path: string
    generated_at: string
    sections_count: number
  }>> {
    return this.fetch('/api/prd-generator/list')
  }

  /**
   * Delete a generated PRD.
   */
  async deleteGeneratedPRD(generationId: string): Promise<{ deleted: boolean }> {
    return this.fetch(`/api/prd-generator/${generationId}`, {
      method: 'DELETE',
    })
  }
}

export const api = new ApiService()

