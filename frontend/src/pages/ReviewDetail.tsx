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
  Layers,
  Code,
  Eye,
  FileCheck,
  Code2,
  Network,
} from 'lucide-react'
import { useState, useEffect } from 'react'
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
import { api } from '../services/api'
import type { Finding, CollaborationFeatures } from '../types'
import TraceLogPanel from '../components/TraceLogPanel'
import ChatPanel from '../components/chat/ChatPanel'
import ReviewRequestPanel from '../components/review/ReviewRequestPanel'
import ImpactGraph from '../components/review/ImpactGraph'
import VersionHistory from '../components/review/VersionHistory'
import GateStatus from '../components/review/GateStatus'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts'

interface DashboardData {
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
  findings_table: Array<{
    id: string
    severity: string
    title: string
    description?: string
    category: string
    dimension?: string  // security, privacy, compliance, engineering, or architecture
    confidence: string
    recommendation: string
    source_type?: string
    source_reference?: string
    // Detailed LLM fields
    technical_details?: string
    attack_scenario?: string
    business_impact?: string
    affected_components?: string[]
    prerequisites?: string
    implementation_guidance?: string
    references?: string[]
  }>
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
      stride_breakdown?: {
        spoofing?: string[]
        tampering?: string[]
        repudiation?: string[]
        information_disclosure?: string[]
        denial_of_service?: string[]
        elevation_of_privilege?: string[]
      }
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
}

interface ReviewStatus {
  review_id: string
  status: string
  progress: number
  message: string
}

export default function ReviewDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set())
  const [aiOnlyFilter, setAiOnlyFilter] = useState(true) // Default to AI-only for cross-functional reviews
  const [filterInitialized, setFilterInitialized] = useState(false)
  const [selectedDimension, setSelectedDimension] = useState<string | 'all'>('all')
  const [activeTab, setActiveTab] = useState<'findings' | 'pm-tool' | 'impact-graph'>('findings')
  const [expertAskModal, setExpertAskModal] = useState<{ isOpen: boolean; predictionId: string; question: string } | null>(null)
  const [chatOpen, setChatOpen] = useState(false)

  // Fetch collaboration features (to know which features are enabled)
  const { data: collaborationFeatures } = useQuery<CollaborationFeatures>({
    queryKey: ['collaboration-features'],
    queryFn: () => api.getCollaborationFeatures(),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
    retry: false, // Don't retry if API doesn't exist (feature not enabled)
  })

  // Feature flags
  const validationEnabled = collaborationFeatures?.validation ?? false
  const commentsEnabled = collaborationFeatures?.comments ?? false
  const teamAssignmentEnabled = collaborationFeatures?.team_assignment ?? false
  const expertFeedbackEnabled = collaborationFeatures?.expert_feedback ?? false
  const chatEnabled = collaborationFeatures?.product_chat ?? false
  const reviewRequestsEnabled = collaborationFeatures?.review_requests ?? false
  const impactGraphEnabled = collaborationFeatures?.impact_graph ?? false

  // Poll for status while pending/running
  const { data: status } = useQuery<ReviewStatus>({
    queryKey: ['review-status', id],
    queryFn: async () => {
      const res = await fetch(`/api/reviews/${id}/status`)
      if (!res.ok) throw new Error('Failed to fetch status')
      return res.json()
    },
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 2000 // Poll every 2 seconds
    },
  })

  // Fetch dashboard data when completed
  const { data: dashboard, isLoading } = useQuery<DashboardData>({
    queryKey: ['review-dashboard', id],
    queryFn: async () => {
      const res = await fetch(`/api/reviews/${id}/dashboard`)
      if (!res.ok) throw new Error('Failed to fetch review')
      return res.json()
    },
    enabled: status?.status === 'completed',
  })

  // Initialize AI-only filter based on whether LLM was used
  useEffect(() => {
    if (dashboard && !filterInitialized) {
      // If LLM analysis was used, default to showing only AI findings
      const hasLLMFindings = dashboard.findings_table.some(f => f.source_type === 'llm')
      const llmWasUsed = dashboard.llm_analysis?.used === true
      setAiOnlyFilter(llmWasUsed || hasLLMFindings)
      setFilterInitialized(true)
    }
  }, [dashboard, filterInitialized])

  if (status?.status === 'pending' || status?.status === 'running') {
    return <LoadingState status={status} />
  }

  if (status?.status === 'failed') {
    return <ErrorState message={status.message} />
  }

  if (isLoading || !dashboard) {
    return <LoadingState status={{ status: 'loading', progress: 0, message: 'Loading...', review_id: id || '' }} />
  }


  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">
            {dashboard.overview.title}
          </h1>
          <p className="text-surface-400 mt-1">
            Reviewed {new Date(dashboard.overview.reviewed_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <RiskBadge rating={dashboard.overview.risk_rating} />
          <button
            onClick={() => window.open(`/api/reviews/${id}/markdown`, '_blank')}
            className="flex items-center gap-2 px-4 py-2 bg-surface-800 border border-surface-700 
                       rounded-lg text-surface-300 hover:text-white hover:border-surface-600 transition-all"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {(() => {
        const filteredFindings = aiOnlyFilter
          ? dashboard.findings_table.filter(f => f.source_type === 'llm')
          : dashboard.findings_table
        
        const filteredCritical = filteredFindings.filter(f => f.severity === 'critical').length
        const filteredHigh = filteredFindings.filter(f => f.severity === 'high').length
        
        return (
          <div className="grid grid-cols-4 gap-6">
            <StatCard
              label={aiOnlyFilter ? "AI Findings" : "Total Findings"}
              value={filteredFindings.length}
              icon={aiOnlyFilter ? Sparkles : Shield}
              color="primary"
              suffix={aiOnlyFilter && dashboard.overview.total_findings > filteredFindings.length 
                ? ` / ${dashboard.overview.total_findings}` 
                : ''}
            />
            <StatCard
              label="Critical"
              value={filteredCritical}
              icon={AlertTriangle}
              color="red"
              suffix={aiOnlyFilter && dashboard.overview.critical_count > filteredCritical 
                ? ` / ${dashboard.overview.critical_count}` 
                : ''}
            />
            <StatCard
              label="High"
              value={filteredHigh}
              icon={Activity}
              color="orange"
              suffix={aiOnlyFilter && dashboard.overview.high_count > filteredHigh 
                ? ` / ${dashboard.overview.high_count}` 
                : ''}
            />
            <StatCard
              label="Risk Score"
              value={dashboard.risk_gauge.value}
              icon={Activity}
              color="yellow"
              suffix="/100"
            />
          </div>
        )
      })()}

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Severity Distribution */}
        {(() => {
          const filteredFindings = aiOnlyFilter
            ? dashboard.findings_table.filter(f => f.source_type === 'llm')
            : dashboard.findings_table
          
          const filteredSeverityData = dashboard.severity_chart.labels.map((label, i) => ({
            name: label,
            value: filteredFindings.filter(f => {
              const severityMap: Record<string, string> = {
                'critical': 'critical',
                'high': 'high',
                'medium': 'medium',
                'low': 'low',
                'info': 'info',
              }
              return f.severity === severityMap[label.toLowerCase()] || 
                     (label === 'Critical' && f.severity === 'critical') ||
                     (label === 'High' && f.severity === 'high') ||
                     (label === 'Medium' && f.severity === 'medium') ||
                     (label === 'Low' && f.severity === 'low') ||
                     (label === 'Info' && f.severity === 'info')
            }).length,
            color: dashboard.severity_chart.colors[i],
          })).filter(d => d.value > 0)
          
          return (
            <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
              <h3 className="font-semibold text-white mb-4">
                Severity Distribution
                {aiOnlyFilter && (
                  <span className="ml-2 text-xs text-primary-400 font-normal">(AI Only)</span>
                )}
              </h3>
              {filteredSeverityData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={filteredSeverityData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {filteredSeverityData.map((entry, index) => (
                        <Cell key={index} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[200px] text-surface-500">
                  No findings to display
                </div>
              )}
            </div>
          )
        })()}

        {/* Category Distribution */}
        {(() => {
          const filteredFindings = aiOnlyFilter
            ? dashboard.findings_table.filter(f => f.source_type === 'llm')
            : dashboard.findings_table
          
          const categoryCounts: Record<string, number> = {}
          filteredFindings.forEach(f => {
            const cat = f.category.replace(/_/g, ' ')
            categoryCounts[cat] = (categoryCounts[cat] || 0) + 1
          })
          
          const filteredCategoryData = Object.entries(categoryCounts).map(([name, value]) => ({
            name,
            value,
          }))
          
          return (
            <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
              <h3 className="font-semibold text-white mb-4">
                By Category
                {aiOnlyFilter && (
                  <span className="ml-2 text-xs text-primary-400 font-normal">(AI Only)</span>
                )}
              </h3>
              {filteredCategoryData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={filteredCategoryData} layout="vertical">
                    <XAxis type="number" stroke="#64748b" />
                    <YAxis
                      type="category"
                      dataKey="name"
                      stroke="#64748b"
                      width={120}
                      tick={{ fontSize: 12 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar dataKey="value" fill="#14b8a6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[200px] text-surface-500">
                  No findings to display
                </div>
              )}
            </div>
          )
        })()}
      </div>

      {/* Delta Summary */}
      {dashboard.delta_summary.cards && (
        <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
          <h3 className="font-semibold text-white mb-4">Change Analysis</h3>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {dashboard.delta_summary.cards.map((card) => (
              <div
                key={card.label}
                className="p-4 rounded-xl bg-surface-800/50 border border-surface-700"
              >
                <p className="text-sm text-surface-400">{card.label}</p>
                <p className="text-2xl font-bold text-white mt-1">{card.value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-3">
            {dashboard.delta_summary.flags.introduces_pii && (
              <Flag label="Introduces PII" color="red" />
            )}
            {dashboard.delta_summary.flags.modifies_auth && (
              <Flag label="Modifies Auth" color="orange" />
            )}
            {dashboard.delta_summary.flags.expands_attack_surface && (
              <Flag label="Expands Attack Surface" color="yellow" />
            )}
          </div>
        </div>
      )}

      {/* LLM Analysis Section - Compact summaries for all analyzers */}
      {dashboard.llm_analysis && (
        <LLMAnalysisSection
          analysis={dashboard.llm_analysis}
          dimensionsAnalyzed={dashboard.overview.dimensions_analyzed}
          findings={dashboard.findings_table}
        />
      )}

      {/* False Positive Filter Stats */}
      {dashboard.false_positive_filter && (
        <FPFilterStatsSection fpStats={dashboard.false_positive_filter} />
      )}

      {/* Approval Gates */}
      {id && <GateStatus reviewId={id} />}

      {/* Version History */}
      {id && <VersionHistory reviewId={id} />}

      {/* Review Request Panel */}
      {reviewRequestsEnabled && id && <ReviewRequestPanel reviewId={id} />}

      {/* PM Tool Section - Tab Navigation */}
      <div className="bg-surface-900/50 rounded-2xl border border-surface-800 overflow-hidden">
        {/* Tabs */}
        <div className="border-b border-surface-800 flex">
          <button
            onClick={() => setActiveTab('findings')}
            className={`
              flex-1 px-6 py-4 font-medium transition-all
              ${activeTab === 'findings'
                ? 'text-white border-b-2 border-primary-500 bg-surface-900'
                : 'text-surface-400 hover:text-white'
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
                ? 'text-white border-b-2 border-primary-500 bg-surface-900'
                : 'text-surface-400 hover:text-white'
              }
            `}
          >
            PRD Changes
          </button>
          {impactGraphEnabled && (
            <button
              onClick={() => setActiveTab('impact-graph')}
              className={`
                flex-1 px-6 py-4 font-medium transition-all
                ${activeTab === 'impact-graph'
                  ? 'text-white border-b-2 border-primary-500 bg-surface-900'
                  : 'text-surface-400 hover:text-white'
                }
              `}
            >
              Impact Graph
            </button>
          )}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'impact-graph' && impactGraphEnabled && id && (
            <ImpactGraph reviewId={id} />
          )}
          {activeTab === 'findings' && (
            <FindingsTabContent
              dashboard={dashboard}
              id={id || ''}
              expandedFindings={expandedFindings}
              setExpandedFindings={setExpandedFindings}
              aiOnlyFilter={aiOnlyFilter}
              setAiOnlyFilter={setAiOnlyFilter}
              selectedDimension={selectedDimension}
              setSelectedDimension={setSelectedDimension}
              validationEnabled={validationEnabled}
              commentsEnabled={commentsEnabled}
              teamAssignmentEnabled={teamAssignmentEnabled}
              expertFeedbackEnabled={expertFeedbackEnabled}
              queryClient={queryClient}
            />
          )}
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

      {/* Floating Chat Button */}
      {chatEnabled && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-primary-500 text-white shadow-lg 
                     hover:bg-primary-600 transition-all flex items-center justify-center z-40
                     hover:scale-105 active:scale-95"
          title="Ask about this review (Cmd+L)"
        >
          <Sparkles className="w-6 h-6" />
        </button>
      )}

      {/* Chat Side Panel */}
      {chatEnabled && (
        <ChatPanel
          reviewId={id}
          isOpen={chatOpen}
          onClose={() => setChatOpen(false)}
        />
      )}

    </div>
  )
}

// Findings Tab Content Component
function FindingsTabContent({
  dashboard,
  id,
  expandedFindings,
  setExpandedFindings,
  aiOnlyFilter,
  setAiOnlyFilter,
  selectedDimension,
  setSelectedDimension,
  validationEnabled,
  commentsEnabled,
  teamAssignmentEnabled,
  expertFeedbackEnabled,
  queryClient,
}: {
  dashboard: DashboardData
  id: string
  expandedFindings: Set<string>
  setExpandedFindings: (set: Set<string> | ((prev: Set<string>) => Set<string>)) => void
  aiOnlyFilter: boolean
  setAiOnlyFilter: (value: boolean) => void
  selectedDimension: string | 'all'
  setSelectedDimension: (value: string | 'all') => void
  validationEnabled: boolean
  commentsEnabled: boolean
  teamAssignmentEnabled: boolean
  expertFeedbackEnabled: boolean
  queryClient: any
}) {
  return (
    <>
      {/* Header with dimension tabs */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary-400" />
              AI-Powered Findings
            </h3>
            {dashboard.findings_table.length > 0 && 
             dashboard.findings_table.every(f => f.source_type === 'llm') && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary-500/15 border border-primary-500/30 text-primary-400 text-xs font-medium">
                100% AI Analysis
              </span>
            )}
          </div>
          {dashboard.findings_table.length > 0 && (
            <button
              onClick={() => {
                const filteredFindings = dashboard.findings_table.filter(f => 
                  (aiOnlyFilter ? f.source_type === 'llm' : true) &&
                  (selectedDimension === 'all' || f.dimension === selectedDimension)
                )
                
                if (expandedFindings.size === filteredFindings.length) {
                  setExpandedFindings(new Set())
                } else {
                  setExpandedFindings(new Set(filteredFindings.map(f => f.id)))
                }
              }}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface-800 border border-surface-700 
                         rounded-lg text-surface-300 hover:text-white hover:border-surface-600 transition-all"
            >
              <ChevronRight className="w-4 h-4" />
              Toggle All
            </button>
          )}
        </div>

        {/* Dimension Tabs */}
        {dashboard.overview.dimensions_analyzed && dashboard.overview.dimensions_analyzed.length > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedDimension('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedDimension === 'all'
                  ? 'bg-primary-500 text-white'
                  : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
              }`}
            >
              All ({dashboard.findings_table.filter(f => aiOnlyFilter ? f.source_type === 'llm' : true).length})
            </button>
            {dashboard.overview.dimensions_analyzed.includes('security') && (
              <button
                onClick={() => setSelectedDimension('security')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedDimension === 'security'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
                }`}
              >
                <Shield className="w-4 h-4" />
                Security ({dashboard.findings_table.filter(f => f.dimension === 'security' && (aiOnlyFilter ? f.source_type === 'llm' : true)).length})
              </button>
            )}
            {dashboard.overview.dimensions_analyzed.includes('privacy') && (
              <button
                onClick={() => setSelectedDimension('privacy')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedDimension === 'privacy'
                    ? 'bg-purple-500 text-white'
                    : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
                }`}
              >
                <Activity className="w-4 h-4" />
                Privacy ({dashboard.findings_table.filter(f => f.dimension === 'privacy' && (aiOnlyFilter ? f.source_type === 'llm' : true)).length})
              </button>
            )}
            {dashboard.overview.dimensions_analyzed.includes('compliance') && (
              <button
                onClick={() => setSelectedDimension('compliance')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedDimension === 'compliance'
                    ? 'bg-amber-500 text-white'
                    : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
                }`}
              >
                <CheckCircle className="w-4 h-4" />
                Compliance ({dashboard.findings_table.filter(f => f.dimension === 'compliance' && (aiOnlyFilter ? f.source_type === 'llm' : true)).length})
              </button>
            )}
            {dashboard.overview.dimensions_analyzed.includes('engineering') && (
              <button
                onClick={() => setSelectedDimension('engineering')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedDimension === 'engineering'
                    ? 'bg-green-500 text-white'
                    : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
                }`}
              >
                <Code className="w-4 h-4" />
                Engineering ({dashboard.findings_table.filter(f => f.dimension === 'engineering' && (aiOnlyFilter ? f.source_type === 'llm' : true)).length})
              </button>
            )}
            {dashboard.overview.dimensions_analyzed.includes('architecture') && (
              <button
                onClick={() => setSelectedDimension('architecture')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedDimension === 'architecture'
                    ? 'bg-orange-500 text-white'
                    : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
                }`}
              >
                <Layers className="w-4 h-4" />
                Architecture ({dashboard.findings_table.filter(f => f.dimension === 'architecture' && (aiOnlyFilter ? f.source_type === 'llm' : true)).length})
              </button>
            )}
          </div>
        )}
      </div>

      {/* Findings List */}
      {(() => {
        const filteredFindings = dashboard.findings_table.filter(f => 
          (aiOnlyFilter ? f.source_type === 'llm' : true) &&
          (selectedDimension === 'all' || f.dimension === selectedDimension)
        )
        
        return filteredFindings.length > 0 ? (
          <div className="space-y-3">
            {filteredFindings.map((finding) => (
              <FindingRow
                key={finding.id}
                finding={finding as Finding}
                reviewId={id}
                expanded={expandedFindings.has(finding.id)}
                onToggle={() => {
                  setExpandedFindings(prev => {
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
                onFindingUpdated={() => {
                  queryClient.invalidateQueries({ queryKey: ['review-dashboard', id] })
                }}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            {dashboard.llm_analysis?.used && dashboard.findings_table.length === 0 ? (
              <>
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                <p className="text-white font-medium">AI Analysis Complete - No Issues Found!</p>
                <p className="text-surface-400 text-sm">
                  The AI analysis found no significant concerns with this implementation.
                </p>
              </>
            ) : selectedDimension !== 'all' ? (
              <>
                <Shield className="w-12 h-12 text-surface-600 mx-auto mb-4" />
                <p className="text-white font-medium">No {selectedDimension} findings</p>
                <p className="text-surface-400 text-sm">
                  Try selecting a different dimension or view all findings.
                </p>
              </>
            ) : (
              <>
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                <p className="text-white font-medium">No findings!</p>
                <p className="text-surface-400 text-sm">Great job on maintaining secure code.</p>
              </>
            )}
          </div>
        )
      })()}
    </>
  )
}

function LoadingState({ status }: { status: ReviewStatus }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="flex flex-col items-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="w-16 h-16 rounded-full border-4 border-primary-500/30 border-t-primary-500 mb-6"
        />
        <h2 className="text-xl font-semibold text-white mb-2">
          {status.message}
        </h2>
        <div className="w-64 h-2 bg-surface-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500"
            initial={{ width: 0 }}
            animate={{ width: `${status.progress * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <p className="text-surface-400 mt-2">
          {Math.round(status.progress * 100)}% complete
        </p>
      </div>

      {/* Trace log panel */}
      {status.review_id && (
        <div className="w-full max-w-3xl px-4">
          <TraceLogPanel
            traceId={status.review_id}
            endpoint={`/api/reviews/${status.review_id}/traces`}
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
      <AlertTriangle className="w-16 h-16 text-red-400 mb-6" />
      <h2 className="text-xl font-semibold text-white mb-2">Review Failed</h2>
      <p className="text-surface-400 text-center max-w-md">{message}</p>
    </div>
  )
}

function RiskBadge({ rating }: { rating: string }) {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
    HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
    MINIMAL: 'bg-primary-500/20 text-primary-400 border-primary-500/30',
  }

  return (
    <span className={`px-4 py-2 rounded-lg border font-semibold ${colors[rating]}`}>
      {rating} RISK
    </span>
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
    primary: 'from-primary-500/20 to-primary-600/10 border-primary-500/30 text-primary-400',
    red: 'from-red-500/20 to-red-600/10 border-red-500/30 text-red-400',
    orange: 'from-orange-500/20 to-orange-600/10 border-orange-500/30 text-orange-400',
    yellow: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30 text-yellow-400',
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-xl border p-6`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-surface-400 text-sm">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">
            {value}{suffix}
          </p>
        </div>
        <Icon className="w-10 h-10 opacity-50" />
      </div>
    </div>
  )
}

function Flag({ label, color }: { label: string; color: string }) {
  const colors: Record<string, string> = {
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm border ${colors[color]}`}>
      {label}
    </span>
  )
}

function LLMAnalysisSection({
  analysis,
  dimensionsAnalyzed,
  findings,
}: {
  analysis: DashboardData['llm_analysis']
  dimensionsAnalyzed?: string[]
  findings: DashboardData['findings_table']
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  if (!analysis) return null

  // Dimension config for icons and colors
  const dimensionConfig: Record<string, { icon: typeof Shield; color: string; label: string }> = {
    security: { icon: Shield, label: 'Security', color: 'cyan' },
    privacy: { icon: Eye, label: 'Privacy', color: 'purple' },
    compliance: { icon: FileCheck, label: 'Compliance', color: 'amber' },
    engineering: { icon: Code2, label: 'Engineering', color: 'green' },
    architecture: { icon: Network, label: 'Architecture', color: 'orange' },
  }

  const colorClasses: Record<string, string> = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    green: 'bg-green-500/10 text-green-400 border-green-500/30',
    orange: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
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
      className="bg-gradient-to-r from-primary-500/10 to-accent-500/10 rounded-2xl border border-primary-500/30 p-6"
    >
      {/* Header - Always visible */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-primary-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white flex items-center gap-2">
              AI Analysis Summary
              <span className="px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-xs font-medium">
                Powered by {analysis.providers.join(' + ')}
              </span>
            </h3>
            <p className="text-surface-400 text-sm">{analysis.findings_count} total findings across {analyzedDimensions.length} dimension{analyzedDimensions.length > 1 ? 's' : ''}</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800/50 border border-surface-700 text-surface-400 hover:text-white hover:border-surface-600 transition-colors text-sm"
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
                  <span className="px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 text-xs">HIGH</span>
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
            <div className="mt-6 pt-6 border-t border-surface-700 space-y-4">
              {/* Executive Summary */}
              {analysis.summary_details?.executive_summary && (
                <div className="p-4 rounded-xl bg-surface-800/50 border border-surface-700">
                  <h4 className="text-sm font-medium text-surface-400 mb-2">Executive Summary</h4>
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

function FPFilterStatsSection({
  fpStats,
}: {
  fpStats: NonNullable<DashboardData['false_positive_filter']>
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-yellow-400" />
          False Positive Filter
        </h3>
        <span className="px-2 py-0.5 rounded-full bg-yellow-500/15 border border-yellow-500/30 text-yellow-400 text-xs font-medium">
          {fpStats.execution_mode === 'parallel' ? 'Parallel (Majority Vote)' : 'Sequential'}
        </span>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="p-3 rounded-xl bg-surface-800/50 border border-surface-700 text-center">
          <p className="text-2xl font-bold text-white">{fpStats.total_original}</p>
          <p className="text-xs text-surface-400 mt-1">Raw Findings</p>
        </div>
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-center">
          <p className="text-2xl font-bold text-red-400">{fpStats.total_removed}</p>
          <p className="text-xs text-surface-400 mt-1">Removed</p>
        </div>
        <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-center">
          <p className="text-2xl font-bold text-yellow-400">{fpStats.total_downgraded}</p>
          <p className="text-xs text-surface-400 mt-1">Downgraded</p>
        </div>
        <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-center">
          <p className="text-2xl font-bold text-green-400">{fpStats.total_final}</p>
          <p className="text-xs text-surface-400 mt-1">Final Findings</p>
        </div>
      </div>

      {/* Removal rate bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-surface-400">Noise Removal Rate</span>
          <span className="text-white font-medium">{Math.round(fpStats.removal_rate * 100)}%</span>
        </div>
        <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-yellow-500 to-green-500 rounded-full transition-all"
            style={{ width: `${Math.round(fpStats.removal_rate * 100)}%` }}
          />
        </div>
      </div>

      {/* Per-dimension breakdown */}
      {fpStats.by_dimension.length > 1 && (
        <div className="space-y-2">
          <p className="text-xs text-surface-500 font-medium uppercase tracking-wide">By Dimension</p>
          {fpStats.by_dimension.map((dim) => (
            <div
              key={dim.dimension}
              className="flex items-center justify-between p-2 rounded-lg bg-surface-800/30 text-sm"
            >
              <span className="text-surface-300 capitalize font-medium w-28">{dim.dimension}</span>
              <span className="text-surface-400">
                {dim.original_count} &rarr; {dim.final_count}
              </span>
              <span className="text-red-400 text-xs">-{dim.removed} removed</span>
              {dim.downgraded > 0 && (
                <span className="text-yellow-400 text-xs">{dim.downgraded} downgraded</span>
              )}
              <span className="text-surface-500 text-xs">{dim.strategies_run} strategies</span>
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
  validationEnabled,
  commentsEnabled,
  teamAssignmentEnabled,
  expertFeedbackEnabled,
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
    high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }

  const dimensionColors: Record<string, string> = {
    security: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    privacy: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    compliance: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    engineering: 'bg-green-500/10 text-green-400 border-green-500/30',
    architecture: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  }

  const dimensionLabels: Record<string, string> = {
    security: 'Security',
    privacy: 'Privacy',
    compliance: 'Compliance',
    engineering: 'Engineering',
    architecture: 'Architecture',
  }

  const isAI = finding.source_type === 'llm'
  const dimension = finding.dimension || 'security'

  return (
    <div className={`rounded-xl bg-surface-800/50 border overflow-hidden ${isAI ? 'border-primary-500/30' : 'border-surface-700'}`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 rounded text-xs font-medium border ${severityColors[finding.severity]}`}>
            {finding.severity.toUpperCase()}
          </span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium border ${dimensionColors[dimension]}`}>
            {dimensionLabels[dimension]}
          </span>
          <span className="text-white font-medium">{finding.title}</span>
          {isAI && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary-500/10 border border-primary-500/30">
              <Sparkles className="w-3 h-3 text-primary-400" />
              <span className="text-xs text-primary-400">AI</span>
            </span>
          )}
          {/* Validation status badge */}
          {finding.validationStatus && finding.validationStatus !== 'pending' && (
            <ValidationStatusBadge status={finding.validationStatus} />
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
          <span className="text-surface-400 text-sm hidden md:block">{finding.category}</span>
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-surface-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-surface-400" />
          )}
        </div>
      </button>
      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="px-4 pb-4 border-t border-surface-700"
        >
          <div className="pt-4 space-y-4">
            {/* Description */}
            {finding.description && (
              <div>
                <p className="text-sm font-medium text-surface-400 mb-2">Description</p>
                <p className="text-white text-sm leading-relaxed">{finding.description}</p>
              </div>
            )}

            {/* Technical Details */}
            {finding.technical_details && (
              <div className="p-3 rounded-lg bg-surface-900/50 border border-surface-700">
                <p className="text-sm font-medium text-primary-400 mb-2">Technical Details</p>
                <p className="text-surface-300 text-sm leading-relaxed">{finding.technical_details}</p>
              </div>
            )}

            {/* Attack Scenario */}
            {finding.attack_scenario && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                <p className="text-sm font-medium text-red-400 mb-2">Attack Scenario</p>
                <p className="text-red-200 text-sm leading-relaxed">{finding.attack_scenario}</p>
              </div>
            )}

            {/* Business Impact */}
            {finding.business_impact && (
              <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
                <p className="text-sm font-medium text-orange-400 mb-2">Business Impact</p>
                <p className="text-orange-200 text-sm leading-relaxed">{finding.business_impact}</p>
              </div>
            )}

            {/* Affected Components */}
            {finding.affected_components && finding.affected_components.length > 0 && (
              <div>
                <p className="text-sm font-medium text-surface-400 mb-2">Affected Components</p>
                <div className="flex flex-wrap gap-2">
                  {finding.affected_components.map((comp, i) => (
                    <span key={i} className="px-2 py-1 rounded-md bg-surface-700 text-surface-300 text-xs">
                      {comp}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Prerequisites */}
            {finding.prerequisites && (
              <div>
                <p className="text-sm font-medium text-surface-400 mb-1">Attack Prerequisites</p>
                <p className="text-surface-300 text-sm">{finding.prerequisites}</p>
              </div>
            )}

            {/* Recommendation */}
            {finding.recommendation && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <p className="text-sm font-medium text-green-400 mb-2">Recommendation</p>
                <p className="text-green-200 text-sm leading-relaxed">{finding.recommendation}</p>
              </div>
            )}

            {/* Implementation Guidance */}
            {finding.implementation_guidance && (
              <div className="p-3 rounded-lg bg-primary-500/10 border border-primary-500/30">
                <p className="text-sm font-medium text-primary-400 mb-2">Implementation Guidance</p>
                <p className="text-primary-200 text-sm leading-relaxed">{finding.implementation_guidance}</p>
              </div>
            )}

            {/* References */}
            {finding.references && finding.references.length > 0 && (
              <div>
                <p className="text-sm font-medium text-surface-400 mb-2">References</p>
                <ul className="space-y-1">
                  {finding.references.map((ref, i) => (
                    <li key={i} className="text-xs text-primary-400 hover:text-primary-300">
                      {ref.startsWith('http') ? (
                        <a href={ref} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                          <ExternalLink className="w-3 h-3" />
                          {ref}
                        </a>
                      ) : (
                        <span>• {ref}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Confidence */}
            <div className="flex items-center gap-4 pt-2 border-t border-surface-700">
              <div>
                <p className="text-xs text-surface-500">Confidence</p>
                <p className="text-sm text-white font-medium">{finding.confidence}</p>
              </div>
              <div>
                <p className="text-xs text-surface-500">Category</p>
                <p className="text-sm text-white font-medium">{finding.category}</p>
              </div>
            </div>

            {/* Collaboration Components - only render if features are enabled */}
            
            {/* Validation Panel (Phase 1) */}
            <FindingValidationPanel
              finding={finding}
              reviewId={reviewId}
              enabled={validationEnabled ?? false}
              onValidated={onFindingUpdated}
            />

            {/* Team Assignment Panel (Phase 3) */}
            <TeamAssignmentPanel
              finding={finding}
              reviewId={reviewId}
              enabled={teamAssignmentEnabled ?? false}
              onAssigned={onFindingUpdated}
            />

            {/* Comments Thread (Phase 2) */}
            <CommentsThread
              finding={finding}
              reviewId={reviewId}
              enabled={commentsEnabled ?? false}
            />

            {/* Expert Feedback Form (Phase 4) */}
            <ExpertFeedbackForm
              finding={finding}
              reviewId={reviewId}
              enabled={expertFeedbackEnabled ?? false}
              onFeedbackSubmitted={onFindingUpdated}
            />
          </div>
        </motion.div>
      )}
    </div>
  )
}

