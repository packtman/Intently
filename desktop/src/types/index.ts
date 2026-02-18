// Core types for Intently Desktop

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

export interface ParsedIntent {
  title: string
  summary: string
  features: string[]
  user_stories: string[]
  data_entities: Array<{
    name: string
    type: string
    is_sensitive: boolean
  }>
  api_changes: string[]
  auth_requirements: string[]
  external_integrations: string[]
}

// Code reference with detailed vulnerability information (from deep threat analyzer)
export interface CodeReference {
  file: string
  line_start?: number
  line_end?: number
  function_name?: string
  class_name?: string
  code_snippet?: string
  issue?: string
  why_vulnerable?: string
  suggested_fix?: string
}

// Remediation step for implementation
export interface RemediationStep {
  step: number
  action: string
  code_changes?: string
  files_to_modify?: string[]
  estimated_effort?: string
}

// Comprehensive remediation strategy
export interface RemediationStrategy {
  summary: string
  detailed_strategy?: string
  implementation_steps?: RemediationStep[]
  code_example?: string
  alternative_approaches?: Array<{
    approach: string
    pros?: string[]
    cons?: string[]
    when_to_use?: string
  }>
  verification?: {
    how_to_test?: string
    test_cases?: string[]
    security_tests?: string[]
    automated_checks?: string[]
  }
  owner?: string
  effort?: string
  priority?: string
  dependencies?: string[]
  rollback_plan?: string
}

// Attack flow step for visualization
export interface AttackFlowStep {
  step: number
  action: string
  system_response?: string
  exploited_weakness?: string
  code_location?: string
}

// Evidence from PRD and code
export interface ThreatEvidence {
  prd_references?: string[]
  code_evidence?: string
}

// Technical details for a threat
export interface ThreatTechnicalDetails {
  attack_vector?: string
  attack_complexity?: string
  privileges_required?: string
  user_interaction?: string
  prerequisites?: string[]
  exploited_components?: string[]
  data_at_risk?: string[]
  affected_endpoints?: string[]
}

// Impact analysis
export interface ThreatImpact {
  confidentiality?: string
  integrity?: string
  availability?: string
  scope?: string
  business_impact?: string
  user_impact?: string
  regulatory_impact?: string
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
  
  // Deep Threat Analyzer enhanced fields
  stride_category?: string
  likelihood?: string
  cvss_estimate?: number
  prd_trigger?: string
  evidence?: ThreatEvidence
  attack_flow_diagram?: string
  attack_flow_steps?: AttackFlowStep[]
  technical_details_enhanced?: ThreatTechnicalDetails
  impact_analysis?: ThreatImpact
  code_references?: CodeReference[]
  remediation?: RemediationStrategy
  required_mitigations?: Array<{
    action?: string
    owner?: string
    effort?: string
  }>
}

// Cross-functional finding that consolidates related risks across dimensions
export interface CrossFunctionalFinding {
  id: string
  title: string
  description: string
  theme: string  // e.g., "data_protection", "authentication", "logging_audit"
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  affected_dimensions: string[]  // ["security", "privacy", "compliance"]
  dimension_count: number
  cross_functional_score: number
  is_critical_cross_functional: boolean
  // Dimension-specific impacts
  security_impact: string
  privacy_impact: string
  compliance_impact: string
  engineering_impact: string
  architecture_impact: string
  // Source findings
  source_finding_ids: string[]
  source_findings_summary: Array<{
    dimension: string
    title: string
    severity: string
  }>
  // Root cause and recommendations
  root_cause: string
  shared_patterns: string[]
  recommendation: string
  mitigations: string[]
  // Affected components
  affected_components: string[]
  affected_files: string[]
  // Metadata
  confidence: string
  consolidation_method: string
  assigned_teams: string[]
}

// Risk matrix entry for threat prioritization
export interface RiskMatrixEntry {
  threat_id: string
  attack: string
  exploits: string
  impact: string
  likelihood: string
  severity: string
  cvss_estimate?: number
  remediation_complexity?: string
}

// Attack surface change from architecture analysis
export interface AttackSurfaceChange {
  component: string
  current_exposure: string
  proposed_exposure: string
  delta: string
}

// Prioritized mitigation recommendation
export interface PrioritizedMitigation {
  mitigation: string
  addresses: string[]
  owner?: string
  effort?: string
  detailed_implementation?: string
  code_changes_required?: string[]
  timeline?: string
  success_criteria?: string
}

// Deep threat model summary
export interface DeepThreatModelSummary {
  executive_summary?: string
  key_finding?: string
  risk_rating?: string
  current_vs_proposed_flow?: string
  attack_surface_expansion?: AttackSurfaceChange[]
  risk_matrix?: RiskMatrixEntry[]
  priority_1_mitigations?: PrioritizedMitigation[]
  priority_2_mitigations?: PrioritizedMitigation[]
  priority_3_mitigations?: PrioritizedMitigation[]
  pre_launch_checklist?: string[]
  testing_requirements?: string[]
  domain_terms_identified?: string[]
  prd_quotes_analyzed?: string[]
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
  cross_functional_findings?: CrossFunctionalFinding[]
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
    // Per-dimension summaries for compact display
    dimension_summaries?: {
      security?: string
      privacy?: string
      compliance?: string
      engineering?: string
      architecture?: string
    }
  }
  // Deep threat model analysis (enhanced security analysis)
  deep_threat_model?: DeepThreatModelSummary
  // Collaboration features (optional, populated when enabled)
  collaboration_features?: CollaborationFeatures
  validation_stats?: ValidationStats
}

export interface PRDInput {
  content: string
  source_type: 'markdown' | 'notion' | 'gdocs'
  title?: string
}

export interface CodebaseInput {
  path: string
  languages: string[]
  branch?: string
  pr?: number
  github_token?: string
}

export interface ReviewConfig {
  use_llm: boolean
  dimensions: string[]
  compliance_frameworks: string[]
  openai_api_key?: string
  anthropic_api_key?: string
  model_override?: string
  prompt_repetition?: boolean
}

export interface ReviewRequest {
  prd: PRDInput
  codebase: CodebaseInput
  config: ReviewConfig
}

export interface AppSettings {
  contextGraphPath: string
  pythonPath: string
  openaiApiKey: string
  anthropicApiKey: string
  theme: 'dark' | 'light'
  autoStartBackend: boolean
}

// ==================== Collaboration Types ====================
// These types support the team collaboration features (Phase 1+)

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
  // PRD Generator features
  prd_generator?: boolean
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

// ==================== PM-Focused Features Types ====================

export interface PRDChange {
  id: string
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
  file_path: string
  file_name: string
  original_content: string
  current_content: string
  backup_path: string | null
  last_saved_at: string | null
}

export interface SavePRDResult {
  saved: boolean
  file_path: string
  backup_path: string | null
  message: string
}

export interface ApplyChangeResult {
  applied: boolean
  updated_prd: string
  side_by_side_diff: SideBySideDiff
  change_summary: string
}

// ==================== Bulk PRD Analysis Types ====================

export interface BulkPRDFile {
  file_name: string
  content: string
  codebase_path: string | null
  dimensions: string[]
}

export interface BulkAnalysisRequest {
  prds: BulkPRDFile[]
  default_codebase_path: string | null
  default_dimensions: string[]
  max_parallel_reviews?: number
  use_llm: boolean
  use_pattern_matching: boolean
  openai_api_key?: string
  anthropic_api_key?: string
}

export interface SinglePRDResult {
  prd_id: string
  prd_file_name: string
  codebase_path: string | null
  success: boolean
  error_message: string
  total_findings: number
  findings_by_severity: Record<string, number>
  findings_by_dimension: Record<string, number>
  review_id: string
  duration_ms: number
}

export interface BulkAnalysisResult {
  id: string
  total_prds: number
  successful_prds: number
  failed_prds: number
  success_rate: number
  total_findings: number
  findings_by_severity: Record<string, number>
  findings_by_dimension: Record<string, number>
  prd_results: SinglePRDResult[]
  codebases_analyzed: string[]
  default_codebase: string | null
  codebase_selection_counts: Record<string, number>
  parallel_workers_used: number
  total_duration_ms: number
  started_at: string
  completed_at: string | null
}

export interface CodebaseSelection {
  path: string
  name: string
  selection_count: number
  last_selected_at: string
  is_above_threshold: boolean
}

export interface BulkAnalysisConfig {
  enabled: boolean
  max_files: number
  max_parallel_reviews: number
  codebase_auto_default_threshold: number
  smart_codebase_default_enabled: boolean
  current_default_codebase: string | null
  codebase_suggestions: CodebaseSelection[]
}

// ==================== PRD Generator Types ====================

export interface PRDGeneratorRequest {
  codebase_path: string
  languages: string[]
  focus_areas: string[]
  include_api_docs: boolean
  include_data_models: boolean
  include_auth_flow: boolean
  include_architecture: boolean
  output_format: 'markdown' | 'structured'
  detail_level: 'overview' | 'detailed' | 'comprehensive'
}

export interface GeneratedPRDSection {
  id: string
  title: string
  content: string
  subsections?: GeneratedPRDSection[]
  source_files?: string[]
  confidence: number
}

export interface GeneratedPRD {
  id: string
  title: string
  summary: string
  sections: GeneratedPRDSection[]
  metadata: {
    codebase_path: string
    files_analyzed: number
    lines_of_code: number
    languages: string[]
    generated_at: string
    generation_time_ms: number
    ai_provider?: string
    output_file_path?: string
  }
  features: Array<{
    name: string
    description: string
    endpoints?: string[]
    models?: string[]
  }>
  api_documentation: Array<{
    endpoint: string
    method: string
    description: string
    parameters?: Array<{ name: string; type: string; required: boolean }>
    response?: string
  }>
  data_models: Array<{
    name: string
    fields: Array<{ name: string; type: string; description?: string }>
    relationships?: string[]
  }>
  auth_requirements: string[]
  technical_stack: string[]
  dependencies: Array<{ name: string; version: string; purpose: string }>
  output_file_path?: string
}

export interface PRDGeneratorStatus {
  status: 'pending' | 'analyzing' | 'generating' | 'completed' | 'failed'
  progress: number
  current_step: string
  steps_completed: string[]
  error_message?: string
}

export interface PRDGeneratorConfig {
  enabled: boolean
  supported_languages: string[]
  max_files_to_analyze: number
  ai_required: boolean
}

