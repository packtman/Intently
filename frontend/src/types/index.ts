// Core types for Context Graph Web Frontend

export interface Review {
  review_id: string
  title: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  risk_rating: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'MINIMAL'
  findings_count: number
  dimensions: string[]
  security_findings: number
  privacy_findings: number
  compliance_findings: number
  engineering_findings: number
  architecture_findings: number
  reviewed_at: string
}

export interface ReviewStatus {
  review_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
  dimensions?: string[]
}

export interface Finding {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description?: string
  category: string
  dimension?: 'security' | 'privacy' | 'compliance' | 'engineering' | 'architecture'
  confidence: string
  recommendation: string
  source_type?: string
  source_reference?: string
  technical_details?: string
  attack_scenario?: string
  business_impact?: string
  affected_components?: string[]
  prerequisites?: string
  implementation_guidance?: string
  references?: string[]
  // Engineering-specific
  estimated_effort?: string
  complexity_score?: number
  affected_files?: string[]
  // Architecture-specific
  architectural_pattern?: string
  affected_services?: string[]
  breaking_change?: boolean
  // Collaboration fields (optional, populated when collaboration features enabled)
  validationStatus?: 'pending' | 'validated' | 'rejected' | 'needs_discussion' | 'accepted_risk' | 'deferred'
  validatedBy?: string
  validatedAt?: string
  validationNotes?: string
  assignedTeam?: string
  assignedUser?: string
  commentCount?: number
}

export interface DashboardData {
  overview: {
    title: string
    risk_rating: string
    total_findings: number
    critical_count: number
    high_count: number
    reviewed_at: string
    dimensions_analyzed?: string[]
    dimension_counts?: {
      security: number
      privacy: number
      compliance: number
      engineering: number
      architecture: number
    }
  }
  severity_chart: {
    labels: string[]
    data: number[]
    colors: string[]
  }
  category_chart: {
    labels: string[]
    data: number[]
  }
  risk_gauge: {
    value: number
  }
  findings_table: Finding[]
  delta_summary: {
    cards: Array<{
      label: string
      value: number
      icon: string
    }>
    flags: {
      introduces_pii: boolean
      modifies_auth: boolean
      expands_attack_surface: boolean
    }
  }
  false_positive_filter?: {
    enabled: boolean
    execution_mode: string
    total_original: number
    total_final: number
    total_removed: number
    total_downgraded: number
    removal_rate: number
    by_dimension: Array<{
      dimension: string
      execution_mode: string
      original_count: number
      final_count: number
      removed: number
      downgraded: number
      removal_rate: number
      strategies_run: number
    }>
  }
  llm_analysis?: {
    used: boolean
    providers: string[]
    findings_count: number
    consensus_count: number
    total_tokens: number
    latency_ms: number
    threat_analysis?: {
      stride_breakdown?: Record<string, string[]>
      attack_surface?: string[]
      trust_boundaries?: string[]
      data_flow_risks?: string[]
    }
    summary_details?: {
      executive_summary?: string
      key_concerns?: string[]
      positive_observations?: string[]
      missing_considerations?: string[]
    }
    dimension_summaries?: {
      security?: string
      privacy?: string
      compliance?: string
      engineering?: string
      architecture?: string
    }
  }
  // Collaboration features (optional, populated when enabled)
  collaboration_features?: CollaborationFeatures
  validation_stats?: ValidationStats
}

// ==================== Collaboration Types ====================
// These types support the team collaboration features

export interface CollaborationFeatures {
  validation: boolean
  team_assignment: boolean
  comments: boolean
  expert_feedback: boolean
  review_lifecycle: boolean
  cross_team_requests: boolean
  consensus_mode: boolean
  pattern_learning: boolean
  // PM-focused features
  prd_changes?: boolean
  prd_quality_scoring?: boolean
  effort_estimation?: boolean
  expert_assist?: boolean
  pm_pattern_learning?: boolean
  prd_save_to_file?: boolean
  side_by_side_diff?: boolean
  // P0: Core PM Experience
  product_chat?: boolean
  codebase_chat?: boolean
  review_requests?: boolean
  impact_graph?: boolean
  // Interactive Threat Canvas
  threat_canvas?: boolean
}

export interface ValidationStats {
  total_findings: number
  pending: number
  validated: number
  rejected: number
  needs_discussion: number
  accepted_risk: number
  deferred: number
}

export interface FindingValidation {
  id: string
  finding_id: string
  review_id: string
  status: 'pending' | 'validated' | 'rejected' | 'needs_discussion' | 'accepted_risk' | 'deferred'
  validator_id: string
  validator_team: string
  notes: string
  validated_at: string
}

export interface FindingComment {
  id: string
  finding_id: string
  review_id: string
  author_id: string
  author_name: string
  author_team: string
  content: string
  parent_comment_id?: string
  created_at: string
  is_deleted: boolean
}

export interface FindingAssignment {
  id: string
  finding_id: string
  review_id: string
  team: string
  user_id?: string
  assigned_by?: string
  assigned_at: string
}

export interface ExpertFeedback {
  id: string
  finding_id: string
  review_id: string
  feedback_type: 'accuracy' | 'severity' | 'recommendation' | 'context'
  original_value: string
  expert_value: string
  expert_id: string
  expert_team: string
  reasoning: string
  created_at: string
}

// Request/Response types for collaboration API
export interface ValidateFindingRequest {
  status: 'validated' | 'rejected' | 'needs_discussion' | 'accepted_risk' | 'deferred'
  notes: string
  validator_id: string
  validator_team: string
}

export interface AddCommentRequest {
  content: string
  author_id: string
  author_name: string
  author_team: string
  parent_comment_id?: string
}

export interface AssignFindingRequest {
  team: string
  user_id?: string
  assigned_by?: string
}

// ==================== Phase 5: Advanced Features Types ====================

// Review Lifecycle
export type LifecycleState = 'draft' | 'in_review' | 'team_review' | 'awaiting_signoff' | 'approved' | 'blocked'

export interface ReviewLifecycle {
  review_id: string
  state: LifecycleState
  updated_by: string
  updated_at: string
  notes?: string
  has_lifecycle: boolean
}

export interface LifecycleHistoryEntry {
  id: string
  state: LifecycleState
  updated_by: string
  updated_at: string
  notes?: string
}

export interface UpdateLifecycleRequest {
  state: LifecycleState
  updated_by: string
  notes?: string
}

// Cross-Team Requests
export interface ReviewRequest {
  id: string
  review_id: string
  finding_id: string
  requesting_team: string
  target_team: string
  question: string
  requested_by: string
  deadline?: string
  status: 'pending' | 'responded'
  created_at: string
  response?: string
  responded_by?: string
  responded_at?: string
}

export interface CreateReviewRequestRequest {
  finding_id: string
  requesting_team: string
  target_team: string
  question: string
  requested_by: string
  deadline?: string
}

export interface RespondToRequestRequest {
  response: string
  responded_by: string
}

// Consensus Mode
export type ConsensusVote = 'approve' | 'reject' | 'abstain'

export interface ConsensusVoteData {
  id: string
  review_id: string
  finding_id: string
  team: string
  vote: ConsensusVote
  voter_id: string
  notes?: string
  voted_at: string
}

export interface ConsensusStatus {
  review_id: string
  finding_id: string
  votes: Record<string, ConsensusVoteData>
  vote_counts: {
    approve: number
    reject: number
    abstain: number
  }
  total_votes: number
  has_consensus: boolean
}

export interface AddConsensusVoteRequest {
  team: string
  vote: ConsensusVote
  voter_id: string
  notes?: string
}

// Pattern Learning
export interface LearnedPattern {
  id: string
  pattern_type: string
  pattern_signature: string
  decision: string
  conditions: string[]
  reasoning: string
  source_feedback_ids: string[]
  times_applied: number
  created_at: string
  similarity_score?: number
}

export interface PatternInsights {
  total_patterns: number
  by_type: Record<string, number>
  by_decision: Record<string, number>
  most_applied_patterns: Array<{
    pattern_signature: string
    decision: string
    times_applied: number
  }>
}

// ==================== PM-Focused Features Types ====================

export interface CodeEvidence {
  file_path: string
  line_number: number | null
  code_snippet: string
  context: string
}

export interface PRDChange {
  id: string
  question: string  // The predicted question, e.g., "What happens to existing sessions?"
  section: string
  change_type: 'addition' | 'modification' | 'restructure'
  current_text: string
  suggested_text: string
  diff_hunks: Array<{
    operation: 'add' | 'remove' | 'context'
    content: string
    line_number: number | null
  }>
  reasoning: string
  team: string
  severity: 'blocker' | 'likely' | 'possible'
  status: 'open' | 'accepted' | 'rejected' | 'dismissed'
  code_evidence: CodeEvidence[]  // Code snippets that ground this prediction
  prd_file: string  // The PRD file name for display
}

export interface PRDChangesResponse {
  changes: PRDChange[]
  summary: {
    total: number
    by_team: Record<string, number>
    by_severity: Record<string, number>
  }
}

export interface PRDQualityScore {
  score: number
  grade: 'A' | 'B' | 'C' | 'D' | 'F'
  gaps: string[]
  predicted_pushback: number
  blockers: number
  likely_questions: number
  possible_questions: number
}

export interface EffortEstimation {
  total_days: {
    min: number
    likely: number
    max: number
  }
  by_requirement: Array<{
    title: string
    min_days: number
    likely_days: number
    max_days: number
    dimension: string
  }>
  codebase_support: number
  tldr: string
}

export interface ExpertAskRequest {
  prediction_id: string
  expert_id: string
  expert_name: string
  question: string
}

export interface ExpertResponseRequest {
  verdict: 'correct' | 'wrong' | 'partially_right'
  note?: string
}

export interface PMPreferences {
  feedback_teams: string[]
  hidden_teams: string[]
  severity_filter: string[]
  muted_patterns: Array<{
    id: string
    pattern: string
    muted_at: string
  }>
  default_codebase: string | null
}

// ==================== Side-by-Side Diff Types ====================

export interface WordChange {
  start: number
  end: number
  change_type: 'added' | 'removed'
}

export interface DiffLine {
  line_number: number | null
  content: string
  status: 'unchanged' | 'deleted' | 'added' | 'modified' | 'empty'
  word_changes?: WordChange[]
}

export interface DiffStats {
  lines_added: number
  lines_removed: number
  lines_modified: number
}

export interface SideBySideDiff {
  change_id: string
  file_name: string
  section: string
  original_lines: DiffLine[]
  suggested_lines: DiffLine[]
  stats: DiffStats
}

export interface PRDFileInfo {
  has_file_path: boolean
  file_path: string | null
  file_name: string | null
  set_at?: string
}

export interface SavePRDResult {
  saved: boolean
  file_path: string
  backup_path: string | null
  message: string
}

// ==================== Interactive Threat Canvas Types ====================

export type CanvasNodeType = 'actor' | 'process' | 'data_store' | 'external'

export interface CanvasNode {
  id: string
  type: CanvasNodeType
  label: string
  x: number
  y: number
  width: number
  height: number
  properties: Record<string, any>
}

export interface CanvasEdge {
  id: string
  source_id: string
  target_id: string
  label: string
  data_classification: string
  protocol: string
  bidirectional: boolean
}

export interface CanvasTrustBoundary {
  id: string
  label: string
  x: number
  y: number
  width: number
  height: number
  trust_level: number
  color: string
}

export interface ThreatOverlay {
  id: string
  threat_id: string
  category: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  affected_node_ids: string[]
  affected_edge_ids: string[]
  mitigation: string
  confidence: number
  source: 'ai' | 'manual'
}

export interface CanvasState {
  canvas_id: string
  review_id?: string
  title: string
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  boundaries: CanvasTrustBoundary[]
  threats: ThreatOverlay[]
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface CanvasSummary {
  canvas_id: string
  review_id?: string
  title: string
  created_at: string
  updated_at: string
}

export interface SuggestThreatsResponse {
  threats: ThreatOverlay[]
  count: number
  by_category: Record<string, number>
  by_severity: Record<string, number>
}

