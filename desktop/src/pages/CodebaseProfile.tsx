import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  Server,
  Database,
  AlertTriangle,
  TrendingUp,
  RefreshCw,
  Trash2,
  Plus,
  Lock,
  Unlock,
  Eye,
  ChevronDown,
  ChevronUp,
  Layers,
  FileSearch,
  FolderOpen,
} from 'lucide-react'

interface AttackSurface {
  total_endpoints: number
  endpoints: Array<{
    path: string
    method: string
    has_auth: boolean
    handles_pii: boolean
    public: boolean
    review_count: number
  }>
  auth_coverage: number
  pii_endpoints: number
  public_endpoints: number
  auth_patterns: string[]
}

interface EntityInventory {
  total_entities: number
  entities: Array<{
    name: string
    type: string
    is_sensitive: boolean
    source_file: string
    review_count: number
  }>
  sensitive_count: number
  by_type: Record<string, number>
}

interface CumulativeFindings {
  total_findings: number
  by_dimension: Record<string, number>
  by_severity: Record<string, number>
  recurring_categories: Array<{ category: string; count: number }>
}

interface Coverage {
  total_files_in_codebase: number
  files_touched_by_reviews: number
  coverage_percent: number
  endpoints_reviewed: number
  endpoints_total: number
  endpoint_coverage_percent: number
}

interface HistoricalTrend {
  reviews: Array<{
    review_id: string
    date: string
    risk_rating: string
    finding_count: number
    quality_score: number | null
  }>
}

interface CodebaseProfileData {
  id: string
  codebase_path: string
  display_name: string
  attack_surface: AttackSurface
  entity_inventory: EntityInventory
  cumulative_findings: CumulativeFindings
  coverage: Coverage
  historical_trend: HistoricalTrend
  review_count: number
  last_review_id: string | null
  created_at: string
  updated_at: string
}

const DIMENSION_COLORS: Record<string, string> = {
  security: '#ef4444',
  privacy: '#a855f7',
  compliance: '#3b82f6',
  engineering: '#22c55e',
  architecture: '#f97316',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
  info: '#6b7280',
}

const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
  UNKNOWN: '#6b7280',
}

export default function CodebaseProfile() {
  const [profiles, setProfiles] = useState<CodebaseProfileData[]>([])
  const [selectedProfile, setSelectedProfile] = useState<CodebaseProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [building, setBuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showBuildForm, setShowBuildForm] = useState(false)
  const [buildPath, setBuildPath] = useState('')
  const [buildName, setBuildName] = useState('')
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000')
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    attackSurface: true,
    entities: true,
    findings: true,
    coverage: true,
    trend: true,
  })

  useEffect(() => {
    if (window.electronAPI?.getBackendUrl) {
      window.electronAPI.getBackendUrl().then(setBaseUrl)
    }
  }, [])

  useEffect(() => {
    fetchProfiles()
  }, [baseUrl])

  const fetchProfiles = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${baseUrl}/api/codebase-profiles`)
      if (!res.ok) {
        if (res.status === 403) throw new Error('Enable FEATURE_CODEBASE_PROFILE=true')
        throw new Error(`HTTP ${res.status}`)
      }
      const data = await res.json()
      setProfiles(data)
      if (data.length > 0 && !selectedProfile) {
        setSelectedProfile(data[0])
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const browsePath = async () => {
    const selected = await window.electronAPI?.selectDirectory()
    if (selected) {
      setBuildPath(selected)
    }
  }

  const buildProfile = async () => {
    if (!buildPath.trim()) return
    setBuilding(true)
    setError(null)
    try {
      const res = await fetch(`${baseUrl}/api/codebase-profiles/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          codebase_path: buildPath.trim(),
          display_name: buildName.trim() || undefined,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const profile = await res.json()
      setSelectedProfile(profile)
      setShowBuildForm(false)
      setBuildPath('')
      setBuildName('')
      await fetchProfiles()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setBuilding(false)
    }
  }

  const deleteProfile = async (profileId: string) => {
    try {
      const res = await fetch(`${baseUrl}/api/codebase-profiles/${profileId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      if (selectedProfile?.id === profileId) setSelectedProfile(null)
      await fetchProfiles()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const rebuildProfile = async (profile: CodebaseProfileData) => {
    setBuilding(true)
    setError(null)
    try {
      const res = await fetch(`${baseUrl}/api/codebase-profiles/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          codebase_path: profile.codebase_path,
          display_name: profile.display_name,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated = await res.json()
      setSelectedProfile(updated)
      await fetchProfiles()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setBuilding(false)
    }
  }

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-6 h-6 border-2 border-neon-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error && profiles.length === 0) {
    return (
      <div className="text-center py-12">
        <Shield className="w-10 h-10 text-void-600 mx-auto mb-3" />
        <p className="text-void-400">{error}</p>
      </div>
    )
  }

  const p = selectedProfile

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-display font-bold text-white">Codebase Profile</h1>
          <p className="text-void-400 mt-2 text-lg">Persistent security & health view across reviews</p>
        </div>
        <button
          onClick={() => setShowBuildForm(!showBuildForm)}
          className="flex items-center gap-2 px-4 py-2 bg-neon-500/10 text-neon-400 border border-neon-500/30 rounded-xl hover:bg-neon-500/20 transition-colors no-drag"
        >
          <Plus className="w-4 h-4" />
          Build Profile
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Build form */}
      {showBuildForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="bg-void-800/50 border border-void-700/50 rounded-xl p-5"
        >
          <h3 className="text-sm font-semibold text-white mb-4">Build New Profile</h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-void-400 mb-1.5 block">Codebase Path</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={buildPath}
                  onChange={e => setBuildPath(e.target.value)}
                  placeholder="/path/to/codebase or github.com/owner/repo"
                  className="flex-1 bg-void-900 border border-void-700 rounded-lg px-3 py-2 text-white text-sm placeholder-void-500 focus:border-neon-500/50 focus:outline-none transition-colors"
                />
                <button
                  onClick={browsePath}
                  className="flex items-center gap-2 px-3 py-2 bg-void-700 border border-void-600 rounded-lg text-void-300 hover:text-white hover:border-neon-500/40 transition-colors text-sm whitespace-nowrap"
                  title="Browse filesystem"
                >
                  <FolderOpen className="w-4 h-4" />
                  Browse
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs text-void-400 mb-1.5 block">Display Name (optional)</label>
              <input
                type="text"
                value={buildName}
                onChange={e => setBuildName(e.target.value)}
                placeholder="My Project"
                className="w-full bg-void-900 border border-void-700 rounded-lg px-3 py-2 text-white text-sm placeholder-void-500 focus:border-neon-500/50 focus:outline-none transition-colors"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={buildProfile}
                disabled={building || !buildPath.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-neon-500 text-void-950 font-medium rounded-lg hover:bg-neon-400 transition-colors disabled:opacity-50 text-sm"
              >
                {building ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <FileSearch className="w-4 h-4" />
                )}
                {building ? 'Building...' : 'Build'}
              </button>
              <button
                onClick={() => setShowBuildForm(false)}
                className="px-4 py-2 text-void-400 hover:text-white transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Profile list sidebar */}
        <div className="col-span-3">
          <div className="bg-void-800/50 border border-void-700/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Profiles</h3>
            {profiles.length === 0 ? (
              <p className="text-xs text-void-500">No profiles yet. Build one above.</p>
            ) : (
              <div className="space-y-2">
                {profiles.map(profile => (
                  <div
                    key={profile.id}
                    onClick={() => setSelectedProfile(profile)}
                    className={`
                      p-3 rounded-xl cursor-pointer transition-all
                      ${selectedProfile?.id === profile.id
                        ? 'bg-neon-500/10 border border-neon-500/30'
                        : 'bg-void-800 border border-void-700 hover:border-void-600'
                      }
                    `}
                  >
                    <p className="text-sm font-medium text-white truncate">{profile.display_name}</p>
                    <p className="text-xs text-void-400 truncate mt-1">{profile.codebase_path}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs text-void-500">{profile.review_count} reviews</span>
                      <span className="text-xs text-void-500">
                        {profile.cumulative_findings.total_findings} findings
                      </span>
                    </div>
                    <div className="flex gap-1 mt-2">
                      <button
                        onClick={e => { e.stopPropagation(); rebuildProfile(profile) }}
                        className="p-1 text-void-500 hover:text-neon-400 transition-colors"
                        title="Rebuild"
                      >
                        <RefreshCw className="w-3 h-3" />
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); deleteProfile(profile.id) }}
                        className="p-1 text-void-500 hover:text-red-400 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Profile detail */}
        <div className="col-span-9 space-y-6">
          {!p ? (
            <div className="text-center py-20">
              <Shield className="w-12 h-12 text-void-700 mx-auto mb-4" />
              <p className="text-void-400">Select or build a profile to view details</p>
            </div>
          ) : (
            <>
              {/* Overview cards */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: 'Reviews', value: p.review_count, icon: Layers },
                  { label: 'Endpoints', value: p.attack_surface.total_endpoints, icon: Server },
                  { label: 'Entities', value: p.entity_inventory.total_entities, icon: Database },
                  { label: 'Findings', value: p.cumulative_findings.total_findings, icon: AlertTriangle },
                ].map(card => (
                  <motion.div
                    key={card.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-void-800/50 border border-void-700/50 rounded-xl p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <card.icon className="w-4 h-4 text-neon-400" />
                      <span className="text-xs text-void-400">{card.label}</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{card.value}</p>
                  </motion.div>
                ))}
              </div>

              {/* Attack Surface */}
              <SectionCard
                title="Attack Surface"
                icon={Shield}
                expanded={expandedSections.attackSurface}
                onToggle={() => toggleSection('attackSurface')}
              >
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <StatBox label="Auth Coverage" value={`${Math.round(p.attack_surface.auth_coverage * 100)}%`} color={p.attack_surface.auth_coverage >= 0.8 ? 'green' : 'yellow'} />
                  <StatBox label="PII Endpoints" value={p.attack_surface.pii_endpoints} color="purple" />
                  <StatBox label="Public Endpoints" value={p.attack_surface.public_endpoints} color={p.attack_surface.public_endpoints > 5 ? 'red' : 'green'} />
                </div>
                {p.attack_surface.endpoints.length > 0 && (
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {p.attack_surface.endpoints.map((ep, i) => (
                      <div key={i} className="flex items-center gap-3 px-3 py-2 bg-void-800 rounded-lg border border-void-700 text-xs">
                        <span className="font-mono text-void-300 w-14 text-center px-1 py-0.5 bg-void-700 rounded">{ep.method}</span>
                        <span className="text-void-300 flex-1 truncate">{ep.path}</span>
                        {ep.has_auth ? (
                          <Lock className="w-3 h-3 text-green-400" />
                        ) : (
                          <Unlock className="w-3 h-3 text-red-400" />
                        )}
                        {ep.handles_pii && <Eye className="w-3 h-3 text-purple-400" />}
                        <span className="text-void-500">{ep.review_count}x</span>
                      </div>
                    ))}
                  </div>
                )}
              </SectionCard>

              {/* Entity Inventory */}
              <SectionCard
                title="Entity Inventory"
                icon={Database}
                expanded={expandedSections.entities}
                onToggle={() => toggleSection('entities')}
              >
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <StatBox label="Total Entities" value={p.entity_inventory.total_entities} color="blue" />
                  <StatBox label="Sensitive" value={p.entity_inventory.sensitive_count} color="red" />
                  <StatBox label="Types" value={Object.keys(p.entity_inventory.by_type).length} color="green" />
                </div>
                {Object.entries(p.entity_inventory.by_type).length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {Object.entries(p.entity_inventory.by_type).map(([type, count]) => (
                      <span key={type} className="text-xs px-2 py-1 bg-void-700 text-void-300 rounded-full capitalize">
                        {type}: {count}
                      </span>
                    ))}
                  </div>
                )}
                {p.entity_inventory.entities.length > 0 && (
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {p.entity_inventory.entities.map((entity, i) => (
                      <div key={i} className="flex items-center gap-3 px-3 py-2 bg-void-800 rounded-lg border border-void-700 text-xs">
                        <span className="text-void-300 flex-1">{entity.name}</span>
                        <span className="text-void-500 capitalize">{entity.type}</span>
                        {entity.is_sensitive && (
                          <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded text-[10px]">sensitive</span>
                        )}
                        <span className="text-void-500">{entity.review_count}x</span>
                      </div>
                    ))}
                  </div>
                )}
              </SectionCard>

              {/* Cumulative Findings */}
              <SectionCard
                title="Cumulative Findings"
                icon={AlertTriangle}
                expanded={expandedSections.findings}
                onToggle={() => toggleSection('findings')}
              >
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-xs font-semibold text-void-400 mb-3">By Dimension</h4>
                    <div className="space-y-2">
                      {Object.entries(p.cumulative_findings.by_dimension).map(([dim, count]) => {
                        const maxCount = Math.max(...Object.values(p.cumulative_findings.by_dimension), 1)
                        return (
                          <div key={dim}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-void-300 capitalize">{dim}</span>
                              <span className="text-void-400">{count}</span>
                            </div>
                            <div className="h-2 bg-void-700 rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${(count / maxCount) * 100}%` }}
                                transition={{ duration: 0.5 }}
                                className="h-full rounded-full"
                                style={{ backgroundColor: DIMENSION_COLORS[dim] || '#6b7280' }}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-void-400 mb-3">By Severity</h4>
                    <div className="space-y-2">
                      {Object.entries(p.cumulative_findings.by_severity).map(([sev, count]) => {
                        const maxCount = Math.max(...Object.values(p.cumulative_findings.by_severity), 1)
                        return (
                          <div key={sev}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-void-300 capitalize">{sev}</span>
                              <span className="text-void-400">{count}</span>
                            </div>
                            <div className="h-2 bg-void-700 rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${(count / maxCount) * 100}%` }}
                                transition={{ duration: 0.5 }}
                                className="h-full rounded-full"
                                style={{ backgroundColor: SEVERITY_COLORS[sev] || '#6b7280' }}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
                {p.cumulative_findings.recurring_categories.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold text-void-400 mb-3">Recurring Categories</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {p.cumulative_findings.recurring_categories.map(cat => (
                        <div key={cat.category} className="flex items-center justify-between px-3 py-2 bg-void-800 rounded-lg border border-void-700">
                          <span className="text-xs text-void-300 capitalize">{cat.category.replace(/_/g, ' ')}</span>
                          <span className="text-xs font-medium text-neon-400">{cat.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </SectionCard>

              {/* Coverage */}
              <SectionCard
                title="Review Coverage"
                icon={FileSearch}
                expanded={expandedSections.coverage}
                onToggle={() => toggleSection('coverage')}
              >
                <div className="grid grid-cols-2 gap-6">
                  <CoverageGauge
                    label="File Coverage"
                    percent={p.coverage.coverage_percent}
                    detail={`${p.coverage.files_touched_by_reviews} / ${p.coverage.total_files_in_codebase} files`}
                  />
                  <CoverageGauge
                    label="Endpoint Coverage"
                    percent={p.coverage.endpoint_coverage_percent}
                    detail={`${p.coverage.endpoints_reviewed} / ${p.coverage.endpoints_total} endpoints`}
                  />
                </div>
              </SectionCard>

              {/* Historical Trend */}
              <SectionCard
                title="Historical Trend"
                icon={TrendingUp}
                expanded={expandedSections.trend}
                onToggle={() => toggleSection('trend')}
              >
                {p.historical_trend.reviews.length === 0 ? (
                  <p className="text-xs text-void-500">No review history yet</p>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-end gap-2 h-32">
                      {p.historical_trend.reviews.map((point, i) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-1">
                          <span className="text-[10px] text-void-400" style={{ color: RISK_COLORS[point.risk_rating] || '#6b7280' }}>
                            {point.risk_rating}
                          </span>
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: `${Math.max((point.finding_count / Math.max(...p.historical_trend.reviews.map(r => r.finding_count), 1)) * 100, 8)}%` }}
                            transition={{ duration: 0.5, delay: i * 0.05 }}
                            className="w-full rounded-t min-h-[4px]"
                            style={{ backgroundColor: RISK_COLORS[point.risk_rating] || '#6b7280' }}
                          />
                          <span className="text-[10px] text-void-500">{point.finding_count}</span>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-1">
                      {p.historical_trend.reviews.slice().reverse().map((point, i) => (
                        <div key={i} className="flex items-center gap-3 text-xs px-3 py-2 bg-void-800 rounded-lg border border-void-700">
                          <span className="text-void-500 w-24">{new Date(point.date).toLocaleDateString()}</span>
                          <span
                            className="px-2 py-0.5 rounded text-[10px] font-medium"
                            style={{
                              backgroundColor: `${RISK_COLORS[point.risk_rating] || '#6b7280'}20`,
                              color: RISK_COLORS[point.risk_rating] || '#6b7280',
                            }}
                          >
                            {point.risk_rating}
                          </span>
                          <span className="text-void-400">{point.finding_count} findings</span>
                          {point.quality_score != null && (
                            <span className="text-void-400 ml-auto">Quality: {point.quality_score}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </SectionCard>

              {/* Metadata */}
              <div className="text-xs text-void-500 flex gap-4">
                <span>Created: {new Date(p.created_at).toLocaleString()}</span>
                <span>Updated: {new Date(p.updated_at).toLocaleString()}</span>
                {p.last_review_id && <span>Last review: {p.last_review_id.slice(0, 8)}</span>}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function SectionCard({
  title,
  icon: Icon,
  expanded,
  onToggle,
  children,
}: {
  title: string
  icon: any
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="bg-void-800/50 border border-void-700/50 rounded-xl">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-5"
      >
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Icon className="w-4 h-4 text-neon-400" />
          {title}
        </h3>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-void-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-void-400" />
        )}
      </button>
      {expanded && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}

function StatBox({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colorClasses: Record<string, string> = {
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    red: 'bg-red-500/10 border-red-500/30 text-red-400',
    yellow: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400',
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
  }
  return (
    <div className={`rounded-lg border p-3 ${colorClasses[color] || colorClasses.blue}`}>
      <p className="text-xs opacity-70 mb-1">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  )
}

function CoverageGauge({ label, percent, detail }: { label: string; percent: number; detail: string }) {
  const clampedPercent = Math.min(Math.max(percent, 0), 100)
  const color = clampedPercent >= 70 ? '#22c55e' : clampedPercent >= 40 ? '#eab308' : '#ef4444'

  return (
    <div className="text-center">
      <div className="relative w-24 h-24 mx-auto mb-2">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="#1a1a2e"
            strokeWidth="3"
          />
          <motion.path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={`${clampedPercent}, 100`}
            initial={{ strokeDasharray: '0, 100' }}
            animate={{ strokeDasharray: `${clampedPercent}, 100` }}
            transition={{ duration: 0.8 }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-white">{Math.round(clampedPercent)}%</span>
        </div>
      </div>
      <p className="text-xs font-medium text-void-300">{label}</p>
      <p className="text-xs text-void-500 mt-0.5">{detail}</p>
    </div>
  )
}
