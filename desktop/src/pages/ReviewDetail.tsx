import { useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  Download,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Activity,
  Sparkles,
  Eye,
  FileCheck,
  Code2,
  Network,
  Link2,
  RefreshCw,
} from 'lucide-react'
import { useState, useEffect, useMemo, Component, ReactNode } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../services/api'
import { useBackend } from '../hooks/useBackend'
import { 
  FindingValidationPanel, 
  ValidationStatusBadge,
  CommentsThread,
  CommentCountBadge,
  TeamAssignmentPanel,
  AssignmentBadge,
  ExpertFeedbackForm,
} from '../components/collaboration'
import {
  PRDChangesView,
  PRDQualityScore,
  EffortEstimation,
  ExpertAskModal,
} from '../components/pm'
import {
  DeepThreatSection,
  EnhancedFindingDetails,
} from '../components/security'
import type { ReviewStatus, DashboardData, Finding, CollaborationFeatures, CrossFunctionalFinding } from '../types'
import TraceLogPanel from '../components/TraceLogPanel'

// Error Boundary to catch any React rendering errors
interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ReviewDetailErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ReviewDetail] Error caught by boundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
          <AlertTriangle className="w-20 h-20 text-red-400 mb-6" />
          <h2 className="text-xl font-display font-semibold text-white mb-2">Something went wrong</h2>
          <p className="text-void-400 text-center max-w-md mb-4">
            An error occurred while displaying the review results.
          </p>
          <p className="text-red-400 text-sm font-mono mb-6 max-w-lg text-center">
            {this.state.error?.message || 'Unknown error'}
          </p>
          <button 
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }} 
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reload Page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// Wrapper component that adds error boundary
export default function ReviewDetail() {
  return (
    <ReviewDetailErrorBoundary>
      <ReviewDetailContent />
    </ReviewDetailErrorBoundary>
  )
}

function ReviewDetailContent() {
  const { id } = useParams()
  const { isConnected } = useBackend()
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set())
  const [aiOnlyFilter, setAiOnlyFilter] = useState(true)
  const [filterInitialized, setFilterInitialized] = useState(false)
  const [selectedDimension, setSelectedDimension] = useState<string | 'all'>('all')
  const [activeTab, setActiveTab] = useState<'findings' | 'pm-tool'>('findings')
  const [expertAskModal, setExpertAskModal] = useState<{ isOpen: boolean; predictionId: string; question: string } | null>(null)
  
  // Track if we've triggered a manual refetch to avoid infinite loops
  const [manualRefetchTriggered, setManualRefetchTriggered] = useState(false)
  const queryClient = useQueryClient()

  // Poll for status while pending/running
  const { data: status, refetch: refetchStatus } = useQuery<ReviewStatus>({
    queryKey: ['review-status', id],
    queryFn: () => api.getReviewStatus(id!),
    enabled: isConnected && !!id,
    // Override global staleTime - status should always be fresh during polling
    staleTime: 0,
    refetchOnMount: 'always',
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 2000
    },
  })

  // Trigger immediate status check on mount
  useEffect(() => {
    if (isConnected && id) {
      refetchStatus()
    }
  }, [isConnected, id, refetchStatus])

  // Fetch dashboard data when completed
  // Use isPending to properly detect when we're waiting for data (React Query v5)
  // isLoading = isPending && isFetching, but isPending alone tells us if there's no cached data
  const { 
    data: dashboard, 
    isLoading, 
    isPending: isDashboardPending,
    isFetching: isDashboardFetching,
    error: dashboardError, 
    refetch: refetchDashboard,
    status: dashboardQueryStatus,
  } = useQuery<DashboardData>({
    queryKey: ['review-dashboard', id],
    queryFn: async () => {
      console.log('[ReviewDetail] Fetching dashboard data for review:', id)
      const result = await api.getReviewDashboard(id!)
      console.log('[ReviewDetail] Dashboard data received:', result ? 'data present' : 'no data')
      return result
    },
    enabled: isConnected && status?.status === 'completed',
    retry: 2,
    retryDelay: 1000,
    // Override global config - always fetch fresh data for dashboard
    staleTime: 0,
    refetchOnMount: 'always',
  })
  
  // Debug logging for state transitions
  useEffect(() => {
    console.log('[ReviewDetail] State:', {
      id,
      isConnected,
      statusStatus: status?.status,
      dashboardQueryStatus,
      isDashboardPending,
      isLoading,
      isDashboardFetching,
      hasDashboard: !!dashboard,
      dashboardError: dashboardError?.message,
    })
  }, [id, isConnected, status?.status, dashboardQueryStatus, isDashboardPending, isLoading, isDashboardFetching, dashboard, dashboardError])

  // Invalidate the reviews list cache when a review finishes so the Dashboard picks it up
  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'failed') {
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    }
  }, [status?.status, queryClient])

  // Force refetch dashboard when status becomes completed
  // This ensures fresh data is always fetched, working around any React Query caching issues
  useEffect(() => {
    if (isConnected && status?.status === 'completed' && !dashboard && !isDashboardFetching && !manualRefetchTriggered) {
      console.log('[ReviewDetail] Status completed, forcing dashboard refetch')
      setManualRefetchTriggered(true)
      // Small delay to ensure React Query has processed the enabled state change
      const timer = setTimeout(() => {
        refetchDashboard()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [isConnected, status?.status, dashboard, isDashboardFetching, refetchDashboard, manualRefetchTriggered])

  // Reset the manual refetch flag when dashboard data arrives
  useEffect(() => {
    if (dashboard && manualRefetchTriggered) {
      setManualRefetchTriggered(false)
    }
  }, [dashboard, manualRefetchTriggered])

  // Fetch collaboration features (to know which features are enabled)
  const { data: collaborationFeatures } = useQuery<CollaborationFeatures>({
    queryKey: ['collaboration-features'],
    queryFn: () => api.getCollaborationFeatures(),
    enabled: isConnected,
    staleTime: 60000, // Cache for 1 minute
    retry: 1,
  })

  // Feature flags
  const validationEnabled = collaborationFeatures?.validation ?? false
  const commentsEnabled = collaborationFeatures?.comments ?? false
  const teamAssignmentEnabled = collaborationFeatures?.team_assignment ?? false
  const expertFeedbackEnabled = collaborationFeatures?.expert_feedback ?? false

  // Initialize AI-only filter based on whether LLM was used
  useEffect(() => {
    if (dashboard && !filterInitialized) {
      const hasLLMFindings = dashboard.findings_table.some((f) => f.source_type === 'llm')
      const llmWasUsed = dashboard.llm_analysis?.used === true
      // Only enable AI filter if there are actual LLM findings
      setAiOnlyFilter(hasLLMFindings && llmWasUsed)
      setFilterInitialized(true)
    }
  }, [dashboard, filterInitialized])

  // Check if selected dimension has LLM findings (engineering/architecture are pattern-only currently)
  const dimensionHasLLMFindings = useMemo(() => {
    if (!dashboard || selectedDimension === 'all') return true
    return dashboard.findings_table.some(
      (f) => f.dimension === selectedDimension && f.source_type === 'llm'
    )
  }, [dashboard, selectedDimension])

  const handleExport = async () => {
    try {
      const { markdown } = await api.getReviewMarkdown(id!)
      const filename = `security-review-${dashboard?.overview.title || id}.md`
      await window.electronAPI?.saveFile(filename, markdown)
      window.electronAPI?.showNotification('Export Complete', `Report saved successfully.`)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertTriangle className="w-16 h-16 text-ember-400 mb-4" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Backend Offline</h2>
        <p className="text-void-400">Start the backend server to view reviews.</p>
      </div>
    )
  }

  if (!status || status?.status === 'pending' || status?.status === 'running') {
    return (
      <LoadingState status={status || { status: 'pending', progress: 0, message: 'Loading review...', review_id: id || '' }} />
    )
  }

  if (status?.status === 'failed') {
    return (
      <ErrorState message={status.message} />
    )
  }

  // Handle unexpected status values - this shouldn't happen but provides a safety net
  if (status?.status !== 'completed') {
    console.error('[ReviewDetail] Unexpected status value:', status?.status)
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertTriangle className="w-16 h-16 text-ember-400 mb-4" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Unexpected Status</h2>
        <p className="text-void-400 mb-4">Review status: {status?.status || 'unknown'}</p>
        <button onClick={() => window.location.reload()} className="btn-secondary">
          Refresh Page
        </button>
      </div>
    )
  }

  if (dashboardError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertTriangle className="w-20 h-20 text-red-400 mb-6" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Failed to Load Dashboard</h2>
        <p className="text-void-400 text-center max-w-md mb-6">{dashboardError.message || 'Could not retrieve review results. Please try again.'}</p>
        <button onClick={() => refetchDashboard()} className="btn-primary">
          Retry
        </button>
      </div>
    )
  }

  // Use isDashboardPending to properly handle the transition from disabled to enabled query
  // This catches the case where enabled just became true but fetch hasn't started yet
  const isWaitingForDashboard = isDashboardPending || isLoading || !dashboard
  
  if (isWaitingForDashboard) {
    return (
      <LoadingState status={{ 
        status: 'pending', 
        progress: isDashboardFetching ? 0.9 : 0.85, 
        message: isDashboardFetching ? 'Loading dashboard data...' : 'Preparing results...', 
        review_id: id || '' 
      }} />
    )
  }

  // Defensive check for required dashboard properties - verify both presence AND meaningful content
  const hasDashboardOverview = dashboard.overview && 
    typeof dashboard.overview === 'object' && 
    ('title' in dashboard.overview || 'risk_rating' in dashboard.overview)
  const hasFindingsTable = Array.isArray(dashboard.findings_table)
  const hasRiskGauge = dashboard.risk_gauge && 
    typeof dashboard.risk_gauge === 'object' && 
    'value' in dashboard.risk_gauge

  if (!hasDashboardOverview || !hasFindingsTable || !hasRiskGauge) {
    console.error('Dashboard data incomplete:', {
      overview: dashboard.overview,
      findings_table: dashboard.findings_table,
      risk_gauge: dashboard.risk_gauge,
    })
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertTriangle className="w-20 h-20 text-ember-400 mb-6" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Incomplete Review Data</h2>
        <p className="text-void-400 text-center max-w-md mb-6">The review completed but returned incomplete data. Try running a new review.</p>
        <button onClick={() => refetchDashboard()} className="btn-secondary">
          Retry Loading
        </button>
      </div>
    )
  }

  // Apply AI filter only if dimension has LLM findings, otherwise show all
  const effectiveAiFilter = aiOnlyFilter && dimensionHasLLMFindings
  const filteredFindings = dashboard.findings_table.filter(
    (f) =>
      (effectiveAiFilter ? f.source_type === 'llm' : true) &&
      (selectedDimension === 'all' || f.dimension === selectedDimension)
  )

  // Safe defaults for dashboard data (in case of partial data)
  const overviewTitle = dashboard.overview.title || 'Untitled Review'
  const reviewedAt = dashboard.overview.reviewed_at 
    ? new Date(dashboard.overview.reviewed_at).toLocaleString() 
    : 'Unknown date'
  const riskRating = dashboard.overview.risk_rating || 'MEDIUM'
  const riskScore = dashboard.risk_gauge.value ?? 0

  // Log that we're about to render the dashboard
  console.log('[ReviewDetail] Rendering dashboard with:', {
    overviewTitle,
    findingsCount: filteredFindings.length,
    riskScore,
  })

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">{overviewTitle}</h1>
          <p className="text-void-400 mt-2">
            Reviewed {reviewedAt}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <RiskBadge rating={riskRating} />
          <button onClick={handleExport} className="btn-secondary flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className={`grid gap-6 ${dashboard.cross_functional_findings && dashboard.cross_functional_findings.length > 0 ? 'grid-cols-5' : 'grid-cols-4'}`}>
        <StatCard
          label={aiOnlyFilter ? 'AI Findings' : 'Total Findings'}
          value={filteredFindings.length}
          icon={aiOnlyFilter ? Sparkles : Shield}
          color="neon"
        />
        <StatCard
          label="Critical"
          value={filteredFindings.filter((f) => f.severity === 'critical').length}
          icon={AlertTriangle}
          color="red"
        />
        <StatCard
          label="High"
          value={filteredFindings.filter((f) => f.severity === 'high').length}
          icon={Activity}
          color="ember"
        />
        {dashboard.cross_functional_findings && dashboard.cross_functional_findings.length > 0 && (
          <StatCard
            label="Cross-Functional"
            value={dashboard.cross_functional_findings.length}
            icon={Link2}
            color="purple"
          />
        )}
        <StatCard
          label="Risk Score"
          value={riskScore}
          icon={Activity}
          color="yellow"
          suffix="/100"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Severity Distribution */}
        <div className="card-glass rounded-2xl p-6">
          <h3 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
            Severity Distribution
            {aiOnlyFilter && <span className="text-xs text-neon-400 font-normal">(AI Only)</span>}
          </h3>
          <SeverityChart findings={filteredFindings} />
        </div>

        {/* Category Distribution */}
        <div className="card-glass rounded-2xl p-6">
          <h3 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
            By Category
            {aiOnlyFilter && <span className="text-xs text-neon-400 font-normal">(AI Only)</span>}
          </h3>
          <CategoryChart findings={filteredFindings} />
        </div>
      </div>

      {/* Delta Summary */}
      {dashboard.delta_summary.cards && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-glass rounded-2xl p-6"
        >
          <h3 className="font-display font-semibold text-white mb-4">Change Analysis</h3>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {dashboard.delta_summary.cards.map((card) => (
              <div key={card.label} className="p-4 rounded-xl bg-void-800/50 border border-void-700">
                <p className="text-sm text-void-400">{card.label}</p>
                <p className="text-2xl font-display font-bold text-white mt-1">{card.value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-3">
            {dashboard.delta_summary.flags.introduces_pii && <Flag label="Introduces PII" color="red" />}
            {dashboard.delta_summary.flags.modifies_auth && <Flag label="Modifies Auth" color="ember" />}
            {dashboard.delta_summary.flags.expands_attack_surface && (
              <Flag label="Expands Attack Surface" color="yellow" />
            )}
          </div>
        </motion.div>
      )}

      {/* LLM Analysis Section - Compact summaries for all analyzers */}
      {dashboard.llm_analysis && (
        <LLMAnalysisSection
          analysis={dashboard.llm_analysis}
          dimensionsAnalyzed={dashboard.overview.dimensions_analyzed}
          findings={dashboard.findings_table}
        />
      )}

      {/* Deep Threat Model Section - Enhanced security analysis */}
      {dashboard.deep_threat_model && (
        <DeepThreatSection threatModel={dashboard.deep_threat_model} />
      )}

      {/* False Positive Filter Stats */}
      {dashboard.false_positive_filter && (
        <FPFilterStatsSection fpStats={dashboard.false_positive_filter} />
      )}

      {/* Cross-Functional Findings Section */}
      {dashboard.cross_functional_findings && dashboard.cross_functional_findings.length > 0 && (
        <CrossFunctionalSection
          findings={dashboard.cross_functional_findings}
        />
      )}

      {/* PM Tool Tab Navigation */}
      <div className="card-glass rounded-2xl overflow-hidden">
        {/* Tabs */}
        <div className="border-b border-void-700 flex">
          <button
            onClick={() => setActiveTab('findings')}
            className={`
              flex-1 px-6 py-4 font-medium transition-all
              ${activeTab === 'findings'
                ? 'text-white border-b-2 border-neon-500 bg-void-900'
                : 'text-void-400 hover:text-white'
              }
            `}
          >
            Findings
          </button>
          <button
            onClick={() => setActiveTab('pm-tool')}
            className={`
              flex-1 px-6 py-4 font-medium transition-all
              ${activeTab === 'pm-tool'
                ? 'text-white border-b-2 border-neon-500 bg-void-900'
                : 'text-void-400 hover:text-white'
              }
            `}
          >
            PRD Changes
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'pm-tool' && id && (
            <div className="space-y-6">
              {/* Quality Score & Effort Estimation */}
              <div className="grid grid-cols-2 gap-6">
                <PRDQualityScore reviewId={id} />
                <EffortEstimation reviewId={id} />
              </div>
              
              {/* PRD Changes */}
              <PRDChangesView
                reviewId={id}
                onAskExpert={(predictionId, question) => {
                  setExpertAskModal({ isOpen: true, predictionId, question })
                }}
              />
            </div>
          )}
          
          {activeTab === 'findings' && (
            <>
      {/* Findings Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header with dimension tabs */}
        <div className="flex flex-col gap-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h3 className="font-display font-semibold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-neon-400" />
                AI-Powered Findings
              </h3>
              {dashboard.findings_table.length > 0 &&
                dashboard.findings_table.every((f) => f.source_type === 'llm') && (
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-neon-500/15 border border-neon-500/30 text-neon-400 text-xs font-medium">
                    100% AI Analysis
                  </span>
                )}
            </div>
            {filteredFindings.length > 0 && (
              <button
                onClick={() => {
                  if (expandedFindings.size === filteredFindings.length) {
                    setExpandedFindings(new Set())
                  } else {
                    setExpandedFindings(new Set(filteredFindings.map((f) => f.id)))
                  }
                }}
                className="btn-secondary text-sm py-2"
              >
                <ChevronRight className="w-4 h-4 inline mr-1" />
                Toggle All
              </button>
            )}
          </div>

          {/* Dimension Tabs - always show so user knows what was analyzed */}
          {dashboard.overview.dimensions_analyzed && dashboard.overview.dimensions_analyzed.length >= 1 && (
            <div className="flex items-center gap-2">
              <DimensionTab
                label="All"
                count={dashboard.findings_table.filter((f) => (aiOnlyFilter ? f.source_type === 'llm' : true)).length}
                isSelected={selectedDimension === 'all'}
                onClick={() => setSelectedDimension('all')}
                color="neon"
              />
              {dashboard.overview.dimensions_analyzed.includes('security') && (
                <DimensionTab
                  label="Security"
                  icon={Shield}
                  count={
                    dashboard.findings_table.filter(
                      (f) => f.dimension === 'security' && (aiOnlyFilter ? f.source_type === 'llm' : true)
                    ).length
                  }
                  isSelected={selectedDimension === 'security'}
                  onClick={() => setSelectedDimension('security')}
                  color="cyan"
                />
              )}
              {dashboard.overview.dimensions_analyzed.includes('privacy') && (
                <DimensionTab
                  label="Privacy"
                  icon={Eye}
                  count={
                    dashboard.findings_table.filter(
                      (f) => f.dimension === 'privacy' && (aiOnlyFilter ? f.source_type === 'llm' : true)
                    ).length
                  }
                  isSelected={selectedDimension === 'privacy'}
                  onClick={() => setSelectedDimension('privacy')}
                  color="aurora"
                />
              )}
              {dashboard.overview.dimensions_analyzed.includes('compliance') && (
                <DimensionTab
                  label="Compliance"
                  icon={FileCheck}
                  count={
                    dashboard.findings_table.filter(
                      (f) => f.dimension === 'compliance' && (aiOnlyFilter ? f.source_type === 'llm' : true)
                    ).length
                  }
                  isSelected={selectedDimension === 'compliance'}
                  onClick={() => setSelectedDimension('compliance')}
                  color="ember"
                />
              )}
              {dashboard.overview.dimensions_analyzed.includes('engineering') && (
                <DimensionTab
                  label="Engineering"
                  icon={Code2}
                  count={
                    dashboard.findings_table.filter(
                      (f) => f.dimension === 'engineering' && (aiOnlyFilter ? f.source_type === 'llm' : true)
                    ).length
                  }
                  isSelected={selectedDimension === 'engineering'}
                  onClick={() => setSelectedDimension('engineering')}
                  color="yellow"
                />
              )}
              {dashboard.overview.dimensions_analyzed.includes('architecture') && (
                <DimensionTab
                  label="Architecture"
                  icon={Network}
                  count={
                    dashboard.findings_table.filter(
                      (f) => f.dimension === 'architecture' && (aiOnlyFilter ? f.source_type === 'llm' : true)
                    ).length
                  }
                  isSelected={selectedDimension === 'architecture'}
                  onClick={() => setSelectedDimension('architecture')}
                  color="purple"
                />
              )}
            </div>
          )}
        </div>

        {/* Findings List */}
        {filteredFindings.length > 0 ? (
          <div className="space-y-3">
            {filteredFindings.map((finding) => (
              <FindingRow
                key={finding.id}
                finding={finding}
                reviewId={id!}
                expanded={expandedFindings.has(finding.id)}
                onToggle={() => {
                  setExpandedFindings((prev) => {
                    const next = new Set(prev)
                    if (next.has(finding.id)) {
                      next.delete(finding.id)
                    } else {
                      next.add(finding.id)
                    }
                    return next
                  })
                }}
                validationEnabled={validationEnabled}
                commentsEnabled={commentsEnabled}
                teamAssignmentEnabled={teamAssignmentEnabled}
                expertFeedbackEnabled={expertFeedbackEnabled}
                onFindingUpdated={() => refetchDashboard()}
              />
            ))}
          </div>
        ) : (
          <EmptyFindings dashboard={dashboard} selectedDimension={selectedDimension} />
        )}
      </motion.div>
            </>
          )}
        </div>
      </div>

      {/* Expert Ask Modal */}
      {expertAskModal && id && (
        <ExpertAskModal
          isOpen={expertAskModal.isOpen}
          onClose={() => setExpertAskModal(null)}
          predictionId={expertAskModal.predictionId}
          defaultQuestion={expertAskModal.question}
          reviewId={id}
        />
      )}
    </div>
  )
}

function LoadingState({ status }: { status: ReviewStatus }) {
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000')

  useEffect(() => {
    async function fetchBaseUrl() {
      if (window.electronAPI?.getBackendUrl) {
        const url = await window.electronAPI.getBackendUrl()
        setBaseUrl(url)
      }
    }
    fetchBaseUrl()
  }, [])

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="flex flex-col items-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="w-20 h-20 rounded-full border-4 border-neon-500/30 border-t-neon-400 mb-6"
        />
        <h2 className="text-xl font-display font-semibold text-white mb-2">{status.message}</h2>
        <div className="w-72 h-2 bg-void-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-neon-500 to-aurora-500"
            initial={{ width: 0 }}
            animate={{ width: `${status.progress * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <p className="text-void-400 mt-2">{Math.round(status.progress * 100)}% complete</p>
      </div>

      {status.review_id && (
        <div className="w-full max-w-3xl px-4">
          <TraceLogPanel
            traceId={status.review_id}
            endpoint={`${baseUrl}/api/reviews/${status.review_id}/traces`}
            isRunning={status.status === 'running' || status.status === 'pending'}
          />
        </div>
      )}
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <AlertTriangle className="w-20 h-20 text-red-400 mb-6" />
      <h2 className="text-xl font-display font-semibold text-white mb-2">Review Failed</h2>
      <p className="text-void-400 text-center max-w-md">{message}</p>
    </div>
  )
}

function RiskBadge({ rating }: { rating: string }) {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
    HIGH: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
    MINIMAL: 'bg-neon-500/20 text-neon-400 border-neon-500/30',
  }

  return (
    <span className={`px-4 py-2 rounded-xl border font-semibold ${colors[rating]}`}>{rating} RISK</span>
  )
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  suffix = '',
}: {
  label: string
  value: number
  icon: typeof Shield
  color: string
  suffix?: string
}) {
  const colorClasses: Record<string, string> = {
    neon: 'from-neon-500/10 to-neon-600/5 border-neon-500/20',
    red: 'from-red-500/10 to-red-600/5 border-red-500/20',
    ember: 'from-ember-500/10 to-ember-600/5 border-ember-500/20',
    yellow: 'from-yellow-500/10 to-yellow-600/5 border-yellow-500/20',
    purple: 'from-purple-500/10 to-purple-600/5 border-purple-500/20',
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-2xl border p-6`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-void-400 text-sm">{label}</p>
          <p className="text-3xl font-display font-bold text-white mt-1">
            {value}
            {suffix}
          </p>
        </div>
        <Icon className="w-10 h-10 opacity-50 text-void-300" />
      </div>
    </div>
  )
}

function Flag({ label, color }: { label: string; color: string }) {
  const colors: Record<string, string> = {
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    ember: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  }

  return <span className={`px-3 py-1.5 rounded-lg text-sm border ${colors[color]}`}>{label}</span>
}

function SeverityChart({ findings }: { findings: Finding[] }) {
  const severityCounts = findings.reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  const data = [
    { name: 'Critical', value: severityCounts.critical || 0, color: '#ef4444' },
    { name: 'High', value: severityCounts.high || 0, color: '#ff7d11' },
    { name: 'Medium', value: severityCounts.medium || 0, color: '#eab308' },
    { name: 'Low', value: severityCounts.low || 0, color: '#22c55e' },
    { name: 'Info', value: severityCounts.info || 0, color: '#00d9d4' },
  ].filter((d) => d.value > 0)

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-void-500">No findings to display</div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={({ name, value }) => `${name}: ${value}`}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a2e',
            border: '1px solid #2a2a4a',
            borderRadius: '8px',
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

function CategoryChart({ findings }: { findings: Finding[] }) {
  const categoryCounts = findings.reduce(
    (acc, f) => {
      const cat = f.category.replace(/_/g, ' ')
      acc[cat] = (acc[cat] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  const data = Object.entries(categoryCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-void-500">No findings to display</div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} layout="vertical">
        <XAxis type="number" stroke="#64748b" />
        <YAxis type="category" dataKey="name" stroke="#64748b" width={120} tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a2e',
            border: '1px solid #2a2a4a',
            borderRadius: '8px',
          }}
        />
        <Bar dataKey="value" fill="#00d9d4" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function LLMAnalysisSection({
  analysis,
  dimensionsAnalyzed,
  findings,
}: {
  analysis: DashboardData['llm_analysis']
  dimensionsAnalyzed?: string[]
  findings: Finding[]
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  if (!analysis) return null

  // Dimension config for icons and colors
  const dimensionConfig: Record<string, { icon: typeof Shield; color: string; label: string }> = {
    security: { icon: Shield, label: 'Security', color: 'cyan' },
    privacy: { icon: Eye, label: 'Privacy', color: 'aurora' },
    compliance: { icon: FileCheck, label: 'Compliance', color: 'ember' },
    engineering: { icon: Code2, label: 'Engineering', color: 'yellow' },
    architecture: { icon: Network, label: 'Architecture', color: 'purple' },
  }

  const colorClasses: Record<string, string> = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    aurora: 'bg-aurora-500/10 text-aurora-400 border-aurora-500/30',
    ember: 'bg-ember-500/10 text-ember-400 border-ember-500/30',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  }

  // Generate summary for each dimension based on findings
  const getDimensionSummary = (dimension: string): string => {
    // First check if backend provided a summary
    if (analysis.dimension_summaries?.[dimension as keyof typeof analysis.dimension_summaries]) {
      return analysis.dimension_summaries[dimension as keyof typeof analysis.dimension_summaries]!
    }
    
    // Otherwise generate from findings
    const dimFindings = findings.filter(f => f.dimension === dimension)
    const criticalCount = dimFindings.filter(f => f.severity === 'critical').length
    const highCount = dimFindings.filter(f => f.severity === 'high').length
    
    if (dimFindings.length === 0) {
      return 'No issues identified'
    }
    
    const parts = []
    if (criticalCount > 0) parts.push(`${criticalCount} critical`)
    if (highCount > 0) parts.push(`${highCount} high`)
    
    const otherCount = dimFindings.length - criticalCount - highCount
    if (otherCount > 0) parts.push(`${otherCount} other`)
    
    return `${dimFindings.length} findings: ${parts.join(', ')}`
  }

  const analyzedDimensions = dimensionsAnalyzed || ['security']

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-neon-500/10 to-aurora-500/10 rounded-2xl border border-neon-500/30 p-6"
    >
      {/* Header - Always visible */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-neon-500/20 to-aurora-500/20 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-neon-400" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-white flex items-center gap-2">
              AI Analysis Summary
              <span className="px-2 py-0.5 rounded-full bg-neon-500/20 text-neon-400 text-xs font-medium">
                Powered by {analysis.providers.join(' + ')}
              </span>
            </h3>
            <p className="text-void-400 text-sm">{analysis.findings_count} total findings across {analyzedDimensions.length} dimension{analyzedDimensions.length > 1 ? 's' : ''}</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-void-800/50 border border-void-700 text-void-400 hover:text-white hover:border-void-600 transition-colors text-sm"
        >
          {isExpanded ? 'Collapse' : 'Expand'}
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* Compact Analyzer Summaries - One line per dimension */}
      <div className="mt-4 space-y-2">
        {analyzedDimensions.map((dimension) => {
          const config = dimensionConfig[dimension]
          if (!config) return null
          const Icon = config.icon
          const summary = getDimensionSummary(dimension)
          const dimFindings = findings.filter(f => f.dimension === dimension)
          const hasCritical = dimFindings.some(f => f.severity === 'critical')
          const hasHigh = dimFindings.some(f => f.severity === 'high')
          
          return (
            <div
              key={dimension}
              className={`flex items-center gap-3 p-3 rounded-xl border ${colorClasses[config.color]}`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="font-medium text-sm w-24 flex-shrink-0">{config.label}</span>
              <span className="text-sm opacity-80 flex-1 truncate">{summary}</span>
              <div className="flex items-center gap-2 flex-shrink-0">
                {hasCritical && (
                  <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-xs">CRIT</span>
                )}
                {hasHigh && !hasCritical && (
                  <span className="px-2 py-0.5 rounded-full bg-ember-500/20 text-ember-400 text-xs">HIGH</span>
                )}
                {dimFindings.length === 0 && (
                  <CheckCircle className="w-4 h-4 text-green-400" />
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-6 pt-6 border-t border-void-700 space-y-4">
              {/* Executive Summary */}
              {analysis.summary_details?.executive_summary && (
                <div className="p-4 rounded-xl bg-void-800/50 border border-void-700">
                  <h4 className="text-sm font-medium text-void-400 mb-2">Executive Summary</h4>
                  <p className="text-white text-sm">{analysis.summary_details.executive_summary}</p>
                </div>
              )}

              {/* Key Concerns */}
              {analysis.summary_details?.key_concerns && analysis.summary_details.key_concerns.length > 0 && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
                  <h4 className="text-sm font-medium text-red-400 mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Key Concerns
                  </h4>
                  <ul className="space-y-2">
                    {analysis.summary_details.key_concerns.map((concern, i) => (
                      <li key={i} className="text-sm text-white flex items-start gap-2">
                        <span className="text-red-400 mt-1">-</span>
                        {concern}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Positive Observations */}
              {analysis.summary_details?.positive_observations &&
                analysis.summary_details.positive_observations.length > 0 && (
                  <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                    <h4 className="text-sm font-medium text-green-400 mb-2 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Positive Observations
                    </h4>
                    <ul className="space-y-1">
                      {analysis.summary_details.positive_observations.map((obs, i) => (
                        <li key={i} className="text-sm text-green-300 flex items-start gap-2">
                          <span className="text-green-400 mt-1">+</span>
                          {obs}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function CrossFunctionalSection({
  findings,
}: {
  findings: CrossFunctionalFinding[]
}) {
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set())

  const severityColors: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }

  const dimensionColors: Record<string, string> = {
    security: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40',
    privacy: 'bg-aurora-500/20 text-aurora-400 border-aurora-500/40',
    compliance: 'bg-ember-500/20 text-ember-400 border-ember-500/40',
    engineering: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
    architecture: 'bg-purple-500/20 text-purple-400 border-purple-500/40',
  }

  const criticalCount = findings.filter(f => f.is_critical_cross_functional).length

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-purple-500/10 via-neon-500/10 to-aurora-500/10 rounded-2xl border border-purple-500/30 p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-neon-500/20 flex items-center justify-center">
            <Link2 className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-white flex items-center gap-2">
              Cross-Functional Risks
              <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 text-xs font-medium">
                {findings.length} Consolidated
              </span>
            </h3>
            <p className="text-void-400 text-sm">
              Common risks identified across multiple functional areas
              {criticalCount > 0 && (
                <span className="ml-2 text-red-400">• {criticalCount} critical (3+ dimensions)</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Cross-Functional Findings List */}
      <div className="space-y-3">
        {findings.map((finding) => {
          const isExpanded = expandedFindings.has(finding.id)

          return (
            <div
              key={finding.id}
              className={`rounded-xl bg-void-800/50 border overflow-hidden ${
                finding.is_critical_cross_functional
                  ? 'border-purple-500/50'
                  : 'border-void-700'
              }`}
            >
              <button
                onClick={() => {
                  setExpandedFindings((prev) => {
                    const next = new Set(prev)
                    if (next.has(finding.id)) {
                      next.delete(finding.id)
                    } else {
                      next.add(finding.id)
                    }
                    return next
                  })
                }}
                className="w-full flex items-center justify-between p-4 hover:bg-void-800/70 transition-colors"
              >
                <div className="flex items-center gap-3 flex-wrap">
                  <span
                    className={`px-2 py-1 rounded-lg text-xs font-medium border ${severityColors[finding.severity]}`}
                  >
                    {finding.severity.toUpperCase()}
                  </span>
                  
                  {/* Dimension Tags */}
                  <div className="flex items-center gap-1">
                    {finding.affected_dimensions.map((dim) => (
                      <span
                        key={dim}
                        className={`px-1.5 py-0.5 rounded text-xs font-medium border ${dimensionColors[dim]}`}
                      >
                        {dim.charAt(0).toUpperCase()}
                      </span>
                    ))}
                  </div>
                  
                  <span className="text-white font-medium">{finding.title}</span>
                  
                  {finding.is_critical_cross_functional && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30">
                      <Link2 className="w-3 h-3 text-purple-400" />
                      <span className="text-xs text-purple-400">{finding.dimension_count} Areas</span>
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-void-400 text-sm hidden md:block">
                    {finding.theme.replace(/_/g, ' ')}
                  </span>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-void-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-void-400" />
                  )}
                </div>
              </button>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-void-700 overflow-hidden"
                  >
                    <div className="p-4 space-y-4">
                      {/* Description */}
                      {finding.description && (
                        <div>
                          <p className="text-sm font-medium text-void-400 mb-2">Description</p>
                          <p className="text-white text-sm leading-relaxed whitespace-pre-line">{finding.description}</p>
                        </div>
                      )}

                      {/* Dimension-Specific Impacts */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {finding.security_impact && (
                          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
                            <p className="text-xs font-medium text-cyan-400 mb-1">Security Impact</p>
                            <p className="text-cyan-200 text-sm">{finding.security_impact}</p>
                          </div>
                        )}
                        {finding.privacy_impact && (
                          <div className="p-3 rounded-xl bg-aurora-500/10 border border-aurora-500/30">
                            <p className="text-xs font-medium text-aurora-400 mb-1">Privacy Impact</p>
                            <p className="text-aurora-200 text-sm">{finding.privacy_impact}</p>
                          </div>
                        )}
                        {finding.compliance_impact && (
                          <div className="p-3 rounded-xl bg-ember-500/10 border border-ember-500/30">
                            <p className="text-xs font-medium text-ember-400 mb-1">Compliance Impact</p>
                            <p className="text-ember-200 text-sm">{finding.compliance_impact}</p>
                          </div>
                        )}
                        {finding.engineering_impact && (
                          <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
                            <p className="text-xs font-medium text-yellow-400 mb-1">Engineering Impact</p>
                            <p className="text-yellow-200 text-sm">{finding.engineering_impact}</p>
                          </div>
                        )}
                        {finding.architecture_impact && (
                          <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/30">
                            <p className="text-xs font-medium text-purple-400 mb-1">Architecture Impact</p>
                            <p className="text-purple-200 text-sm">{finding.architecture_impact}</p>
                          </div>
                        )}
                      </div>

                      {/* Root Cause */}
                      {finding.root_cause && (
                        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30">
                          <p className="text-sm font-medium text-red-400 mb-2">Root Cause</p>
                          <p className="text-red-200 text-sm">{finding.root_cause}</p>
                        </div>
                      )}

                      {/* Recommendation */}
                      {finding.recommendation && (
                        <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30">
                          <p className="text-sm font-medium text-green-400 mb-2">Recommendation</p>
                          <p className="text-green-200 text-sm">{finding.recommendation}</p>
                        </div>
                      )}

                      {/* Mitigations */}
                      {finding.mitigations && finding.mitigations.length > 0 && (
                        <div>
                          <p className="text-sm font-medium text-void-400 mb-2">Mitigations</p>
                          <ul className="space-y-1">
                            {finding.mitigations.map((m, i) => (
                              <li key={i} className="text-sm text-neon-300 flex items-start gap-2">
                                <span className="text-neon-400 mt-1">•</span>
                                {m}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Source Findings */}
                      <div className="pt-3 border-t border-void-700">
                        <p className="text-xs text-void-500 mb-2">Consolidated from {finding.source_findings_summary.length} findings:</p>
                        <div className="flex flex-wrap gap-2">
                          {finding.source_findings_summary.map((source, i) => (
                            <span
                              key={i}
                              className={`px-2 py-1 rounded text-xs ${dimensionColors[source.dimension]}`}
                            >
                              [{source.dimension}] {source.title.substring(0, 30)}...
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Metadata */}
                      <div className="flex items-center gap-4 pt-2 border-t border-void-700 text-sm">
                        <div>
                          <p className="text-xs text-void-500">Confidence</p>
                          <p className="text-white font-medium">{finding.confidence}</p>
                        </div>
                        <div>
                          <p className="text-xs text-void-500">Method</p>
                          <p className="text-white font-medium">{finding.consolidation_method}</p>
                        </div>
                        <div>
                          <p className="text-xs text-void-500">Assigned Teams</p>
                          <p className="text-white font-medium">{finding.assigned_teams.join(', ')}</p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

function DimensionTab({
  label,
  icon: Icon,
  count,
  isSelected,
  onClick,
  color,
}: {
  label: string
  icon?: typeof Shield
  count: number
  isSelected: boolean
  onClick: () => void
  color: string
}) {
  const colorClasses: Record<string, { selected: string; default: string }> = {
    neon: { selected: 'bg-neon-500 text-void-950', default: 'text-void-400' },
    cyan: { selected: 'bg-cyan-500 text-void-950', default: 'text-void-400' },
    aurora: { selected: 'bg-aurora-500 text-white', default: 'text-void-400' },
    ember: { selected: 'bg-ember-500 text-void-950', default: 'text-void-400' },
    yellow: { selected: 'bg-yellow-500 text-void-950', default: 'text-void-400' },
    purple: { selected: 'bg-purple-500 text-white', default: 'text-void-400' },
  }

  const styles = colorClasses[color] || colorClasses.neon

  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
        isSelected ? styles.selected : `bg-void-800 ${styles.default} hover:text-white hover:bg-void-700`
      }`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {label} ({count})
    </button>
  )
}

function FPFilterStatsSection({
  fpStats,
}: {
  fpStats: NonNullable<DashboardData['false_positive_filter']>
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-glass rounded-2xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-semibold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-yellow-400" />
          False Positive Filter
        </h3>
        <span className="px-2 py-0.5 rounded-full bg-yellow-500/15 border border-yellow-500/30 text-yellow-400 text-xs font-medium">
          {fpStats.execution_mode === 'parallel' ? 'Parallel (Majority Vote)' : 'Sequential'}
        </span>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="p-3 rounded-xl bg-void-800/50 border border-void-700 text-center">
          <p className="text-2xl font-display font-bold text-white">{fpStats.total_original}</p>
          <p className="text-xs text-void-400 mt-1">Raw Findings</p>
        </div>
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-center">
          <p className="text-2xl font-display font-bold text-red-400">{fpStats.total_removed}</p>
          <p className="text-xs text-void-400 mt-1">Removed</p>
        </div>
        <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-center">
          <p className="text-2xl font-display font-bold text-yellow-400">{fpStats.total_downgraded}</p>
          <p className="text-xs text-void-400 mt-1">Downgraded</p>
        </div>
        <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-center">
          <p className="text-2xl font-display font-bold text-green-400">{fpStats.total_final}</p>
          <p className="text-xs text-void-400 mt-1">Final Findings</p>
        </div>
      </div>

      {/* Removal rate bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-void-400">Noise Removal Rate</span>
          <span className="text-white font-medium">{Math.round(fpStats.removal_rate * 100)}%</span>
        </div>
        <div className="w-full h-2 bg-void-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-yellow-500 to-green-500 rounded-full transition-all"
            style={{ width: `${Math.round(fpStats.removal_rate * 100)}%` }}
          />
        </div>
      </div>

      {/* Per-dimension breakdown */}
      {fpStats.by_dimension.length > 1 && (
        <div className="space-y-2">
          <p className="text-xs text-void-500 font-medium uppercase tracking-wide">By Dimension</p>
          {fpStats.by_dimension.map((dim) => (
            <div
              key={dim.dimension}
              className="flex items-center justify-between p-2 rounded-lg bg-void-800/30 text-sm"
            >
              <span className="text-void-300 capitalize font-medium w-28">{dim.dimension}</span>
              <span className="text-void-400">
                {dim.original_count} &rarr; {dim.final_count}
              </span>
              <span className="text-red-400 text-xs">-{dim.removed} removed</span>
              {dim.downgraded > 0 && (
                <span className="text-yellow-400 text-xs">{dim.downgraded} downgraded</span>
              )}
              <span className="text-void-500 text-xs">{dim.strategies_run} strategies</span>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

function FindingRow({
  finding,
  reviewId,
  expanded,
  onToggle,
  validationEnabled = false,
  commentsEnabled = false,
  teamAssignmentEnabled = false,
  expertFeedbackEnabled = false,
  onFindingUpdated,
}: {
  finding: Finding
  reviewId: string
  expanded: boolean
  onToggle: () => void
  validationEnabled?: boolean
  commentsEnabled?: boolean
  teamAssignmentEnabled?: boolean
  expertFeedbackEnabled?: boolean
  onFindingUpdated?: () => void
}) {
  const severityColors: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }

  const dimensionColors: Record<string, string> = {
    security: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    privacy: 'bg-aurora-500/10 text-aurora-400 border-aurora-500/30',
    compliance: 'bg-ember-500/10 text-ember-400 border-ember-500/30',
  }

  const isAI = finding.source_type === 'llm'
  const dimension = finding.dimension || 'security'

  return (
    <div
      className={`rounded-xl bg-void-800/30 border overflow-hidden ${
        isAI ? 'border-neon-500/30' : 'border-void-700'
      }`}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-void-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span
            className={`px-2 py-1 rounded-lg text-xs font-medium border ${severityColors[finding.severity]}`}
          >
            {finding.severity.toUpperCase()}
          </span>
          <span className={`px-2 py-0.5 rounded-lg text-xs font-medium border ${dimensionColors[dimension]}`}>
            {dimension.charAt(0).toUpperCase() + dimension.slice(1)}
          </span>
          <span className="text-white font-medium">{finding.title}</span>
          {isAI && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-neon-500/10 border border-neon-500/30">
              <Sparkles className="w-3 h-3 text-neon-400" />
              <span className="text-xs text-neon-400">AI</span>
            </span>
          )}
          {/* Validation status badge - only shown when feature enabled */}
          {validationEnabled && finding.validationStatus && (
            <ValidationStatusBadge status={finding.validationStatus} compact />
          )}
          {/* Team assignment badge */}
          {finding.assignedTeam && (
            <AssignmentBadge team={finding.assignedTeam} />
          )}
          {/* Comment count badge */}
          {finding.commentCount !== undefined && finding.commentCount > 0 && (
            <CommentCountBadge count={finding.commentCount} />
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-void-400 text-sm hidden md:block">{finding.category.replace(/_/g, ' ')}</span>
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-void-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-void-400" />
          )}
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-void-700 overflow-hidden"
          >
            <div className="p-4 space-y-4">
              {finding.description && (
                <div>
                  <p className="text-sm font-medium text-void-400 mb-2">Description</p>
                  <p className="text-white text-sm leading-relaxed">{finding.description}</p>
                </div>
              )}

              {finding.technical_details && (
                <div className="p-3 rounded-xl bg-void-900/50 border border-void-700">
                  <p className="text-sm font-medium text-neon-400 mb-2">Technical Details</p>
                  <p className="text-void-300 text-sm leading-relaxed">{finding.technical_details}</p>
                </div>
              )}

              {finding.attack_scenario && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30">
                  <p className="text-sm font-medium text-red-400 mb-2">Attack Scenario</p>
                  <p className="text-red-200 text-sm leading-relaxed">{finding.attack_scenario}</p>
                </div>
              )}

              {finding.business_impact && (
                <div className="p-3 rounded-xl bg-ember-500/10 border border-ember-500/30">
                  <p className="text-sm font-medium text-ember-400 mb-2">Business Impact</p>
                  <p className="text-ember-200 text-sm leading-relaxed">{finding.business_impact}</p>
                </div>
              )}

              {finding.recommendation && (
                <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30">
                  <p className="text-sm font-medium text-green-400 mb-2">Recommendation</p>
                  <p className="text-green-200 text-sm leading-relaxed">{finding.recommendation}</p>
                </div>
              )}

              {finding.implementation_guidance && (
                <div className="p-3 rounded-xl bg-neon-500/10 border border-neon-500/30">
                  <p className="text-sm font-medium text-neon-400 mb-2">Implementation Guidance</p>
                  <p className="text-neon-200 text-sm leading-relaxed">{finding.implementation_guidance}</p>
                </div>
              )}

              {finding.references && finding.references.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-void-400 mb-2">References</p>
                  <ul className="space-y-1">
                    {finding.references.map((ref, i) => (
                      <li key={i} className="text-xs text-neon-400 hover:text-neon-300">
                        {ref.startsWith('http') ? (
                          <button
                            onClick={() => window.electronAPI?.openExternal(ref)}
                            className="flex items-center gap-1"
                          >
                            <ExternalLink className="w-3 h-3" />
                            {ref}
                          </button>
                        ) : (
                          <span>* {ref}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex items-center gap-4 pt-2 border-t border-void-700 text-sm">
                <div>
                  <p className="text-xs text-void-500">Confidence</p>
                  <p className="text-white font-medium">{finding.confidence}</p>
                </div>
              </div>

              {/* Enhanced Deep Threat Analysis Details */}
              <EnhancedFindingDetails
                finding={finding}
                onOpenFile={(file, line) => {
                  // Open file in default editor via Electron
                  window.electronAPI?.openFileInEditor?.(file, line)
                }}
              />

              {/* Collaboration Components - only render if features are enabled */}
              
              {/* Validation Panel (Phase 1) */}
              <FindingValidationPanel
                finding={finding}
                reviewId={reviewId}
                enabled={validationEnabled}
                onValidated={onFindingUpdated}
              />

              {/* Team Assignment Panel (Phase 3) */}
              <TeamAssignmentPanel
                finding={finding}
                reviewId={reviewId}
                enabled={teamAssignmentEnabled}
                onAssigned={onFindingUpdated}
              />

              {/* Comments Thread (Phase 2) */}
              <CommentsThread
                finding={finding}
                reviewId={reviewId}
                enabled={commentsEnabled}
              />

              {/* Expert Feedback Form (Phase 4) */}
              <ExpertFeedbackForm
                finding={finding}
                reviewId={reviewId}
                enabled={expertFeedbackEnabled}
                onFeedbackSubmitted={onFindingUpdated}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function EmptyFindings({
  dashboard,
  selectedDimension,
}: {
  dashboard: DashboardData
  selectedDimension: string | 'all'
}) {
  if (dashboard.llm_analysis?.used && dashboard.findings_table.length === 0) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <p className="text-white font-display font-semibold text-lg">AI Analysis Complete - No Issues Found!</p>
        <p className="text-void-400 text-sm mt-2">
          The AI analysis found no significant concerns with this implementation.
        </p>
      </div>
    )
  }

  if (selectedDimension !== 'all') {
    return (
      <div className="text-center py-12">
        <Shield className="w-16 h-16 text-void-600 mx-auto mb-4" />
        <p className="text-white font-medium">No {selectedDimension} findings</p>
        <p className="text-void-400 text-sm mt-2">
          Try selecting a different dimension or view all findings.
        </p>
      </div>
    )
  }

  return (
    <div className="text-center py-12">
      <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
      <p className="text-white font-display font-semibold text-lg">No findings!</p>
      <p className="text-void-400 text-sm mt-2">Great job on maintaining secure code.</p>
    </div>
  )
}
