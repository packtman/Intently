import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Settings as SettingsIcon,
  Key,
  Zap,
  Save,
  Check,
  AlertCircle,
  RefreshCw,
  Server,
  ToggleLeft,
  ToggleRight,
  Layers,
  Shield,
  Eye,
  FileCheck,
  Code,
  FileText,
  Sparkles,
} from 'lucide-react'

interface FeatureFlags {
  validation: boolean
  team_assignment: boolean
  comments: boolean
  expert_feedback: boolean
  review_lifecycle: boolean
  cross_team_requests: boolean
  consensus_mode: boolean
  pattern_learning: boolean
  prd_changes: boolean
  prd_quality_scoring: boolean
  effort_estimation: boolean
  expert_assist: boolean
  pm_pattern_learning: boolean
  prd_save_to_file: boolean
  side_by_side_diff: boolean
  bulk_prd_analysis: boolean
  bulk_prd_max_files: number
  bulk_prd_max_parallel_reviews: number
  bulk_prd_smart_codebase_default: boolean
  prd_generator: boolean
}

interface ApiKeySettings {
  openaiKey: string
  anthropicKey: string
}

export default function Settings() {
  const queryClient = useQueryClient()
  const [apiKeys, setApiKeys] = useState<ApiKeySettings>({
    openaiKey: '',
    anthropicKey: '',
  })
  const [saved, setSaved] = useState(false)

  // Fetch feature flags
  const { data: features, isLoading: loadingFeatures, refetch: refetchFeatures } = useQuery({
    queryKey: ['features'],
    queryFn: async () => {
      const res = await fetch('/api/features')
      if (!res.ok) throw new Error('Failed to fetch features')
      return res.json() as Promise<FeatureFlags>
    },
  })

  // Fetch backend health
  const { data: health, isLoading: loadingHealth, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch('/api/health')
      if (!res.ok) throw new Error('Backend offline')
      return res.json()
    },
    retry: false,
    refetchInterval: 30000, // Check every 30 seconds
  })

  const isConnected = !!health

  const handleSaveApiKeys = async () => {
    // Store in localStorage for now (in production, use secure storage)
    localStorage.setItem('openai_api_key', apiKeys.openaiKey)
    localStorage.setItem('anthropic_api_key', apiKeys.anthropicKey)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  useEffect(() => {
    // Load API keys from localStorage
    const openaiKey = localStorage.getItem('openai_api_key') || ''
    const anthropicKey = localStorage.getItem('anthropic_api_key') || ''
    setApiKeys({ openaiKey, anthropicKey })
  }, [])

  const featureGroups = [
    {
      title: 'Review Dimensions',
      icon: Layers,
      color: 'primary',
      features: [
        { key: 'validation', label: 'Finding Validation', description: 'Allow users to validate/reject AI findings' },
        { key: 'team_assignment', label: 'Team Assignment', description: 'Route findings to appropriate team queues' },
        { key: 'comments', label: 'Comments', description: 'Enable threaded discussions on findings' },
      ],
    },
    {
      title: 'Collaboration',
      icon: Shield,
      color: 'purple',
      features: [
        { key: 'expert_feedback', label: 'Expert Feedback', description: 'Capture corrections and reasoning for learning' },
        { key: 'review_lifecycle', label: 'Review Lifecycle', description: 'Add approval gates and workflow states' },
        { key: 'cross_team_requests', label: 'Cross-Team Requests', description: 'Request input from other teams' },
        { key: 'consensus_mode', label: 'Consensus Mode', description: 'Require validation from multiple teams' },
      ],
    },
    {
      title: 'PM Tools',
      icon: FileText,
      color: 'green',
      features: [
        { key: 'prd_changes', label: 'PRD Changes', description: 'Convert findings into actionable PRD changes' },
        { key: 'prd_quality_scoring', label: 'PRD Quality Scoring', description: 'Calculate readiness score and identify gaps' },
        { key: 'effort_estimation', label: 'Effort Estimation', description: 'Code-grounded time estimates' },
        { key: 'expert_assist', label: 'Expert Assist', description: 'Lightweight expert validation' },
        { key: 'side_by_side_diff', label: 'Side-by-Side Diff', description: 'Compare original vs suggested PRD changes' },
      ],
    },
    {
      title: 'Bulk Analysis',
      icon: Sparkles,
      color: 'orange',
      features: [
        { key: 'bulk_prd_analysis', label: 'Bulk PRD Analysis', description: 'Analyze up to 20 PRD files in parallel' },
        { key: 'bulk_prd_smart_codebase_default', label: 'Smart Codebase Default', description: 'Auto-detect default codebase from usage' },
        { key: 'prd_generator', label: 'PRD Generator', description: 'Generate PRD documents from codebases' },
      ],
    },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">Settings</h1>
        <p className="text-surface-400 mt-2">Configure Context Graph features and API keys</p>
      </div>

      {/* Backend Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                isConnected ? 'bg-green-500/20' : 'bg-red-500/20'
              }`}
            >
              <Server className={`w-6 h-6 ${isConnected ? 'text-green-400' : 'text-red-400'}`} />
            </div>
            <div>
              <h2 className="font-semibold text-white">Backend Server</h2>
              <p className={`text-sm ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                {loadingHealth ? 'Checking...' : isConnected ? 'Online' : 'Offline'}
              </p>
            </div>
          </div>
          <button
            onClick={() => refetchHealth()}
            disabled={loadingHealth}
            className="p-2 rounded-lg bg-surface-800 border border-surface-700 text-surface-400 
                       hover:text-white hover:border-surface-600 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loadingHealth ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </motion.div>

      {/* Feature Flags */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6 space-y-6"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h2 className="font-semibold text-white">Feature Flags</h2>
              <p className="text-sm text-surface-400">Current feature configuration (read-only)</p>
            </div>
          </div>
          <button
            onClick={() => refetchFeatures()}
            disabled={loadingFeatures}
            className="p-2 rounded-lg bg-surface-800 border border-surface-700 text-surface-400 
                       hover:text-white hover:border-surface-600 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loadingFeatures ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {loadingFeatures ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-surface-500 animate-spin" />
          </div>
        ) : features ? (
          <div className="space-y-6">
            {featureGroups.map((group) => {
              const Icon = group.icon
              const colorClasses = {
                primary: 'bg-primary-500/10 border-primary-500/30 text-primary-400',
                purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
                green: 'bg-green-500/10 border-green-500/30 text-green-400',
                orange: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
              }
              
              return (
                <div key={group.title}>
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className={`w-4 h-4 ${
                      group.color === 'primary' ? 'text-primary-400' :
                      group.color === 'purple' ? 'text-purple-400' :
                      group.color === 'green' ? 'text-green-400' :
                      'text-orange-400'
                    }`} />
                    <h3 className="text-sm font-medium text-surface-300">{group.title}</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {group.features.map((feature) => {
                      const isEnabled = features[feature.key as keyof FeatureFlags]
                      return (
                        <div
                          key={feature.key}
                          className={`flex items-center justify-between p-3 rounded-lg border ${
                            isEnabled
                              ? colorClasses[group.color as keyof typeof colorClasses]
                              : 'bg-surface-800/50 border-surface-700 text-surface-500'
                          }`}
                        >
                          <div className="flex-1 min-w-0 mr-3">
                            <p className={`text-sm font-medium ${isEnabled ? 'text-white' : 'text-surface-400'}`}>
                              {feature.label}
                            </p>
                            <p className="text-xs text-surface-500 truncate">{feature.description}</p>
                          </div>
                          {isEnabled ? (
                            <ToggleRight className="w-5 h-5 flex-shrink-0" />
                          ) : (
                            <ToggleLeft className="w-5 h-5 flex-shrink-0" />
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-sm text-red-300">Failed to load feature flags. Is the backend running?</p>
          </div>
        )}

        <div className="p-4 rounded-lg bg-surface-800/50 border border-surface-700">
          <p className="text-xs text-surface-400">
            Feature flags are configured via environment variables. To enable a feature, set the corresponding
            environment variable (e.g., <code className="text-primary-400">FEATURE_BULK_PRD_ANALYSIS=true</code>)
            and restart the backend server.
          </p>
        </div>
      </motion.div>

      {/* API Keys */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
            <Key className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h2 className="font-semibold text-white">API Keys</h2>
            <p className="text-sm text-surface-400">Configure AI provider API keys</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">OpenAI API Key</label>
            <input
              type="password"
              value={apiKeys.openaiKey}
              onChange={(e) => setApiKeys({ ...apiKeys, openaiKey: e.target.value })}
              placeholder="sk-..."
              className="w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                       text-white placeholder-surface-500 font-mono text-sm
                       focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
            />
            <p className="text-xs text-surface-500 mt-1">
              Get your key from{' '}
              <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" 
                 className="text-primary-400 hover:underline">
                platform.openai.com
              </a>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">Anthropic API Key</label>
            <input
              type="password"
              value={apiKeys.anthropicKey}
              onChange={(e) => setApiKeys({ ...apiKeys, anthropicKey: e.target.value })}
              placeholder="sk-ant-..."
              className="w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                       text-white placeholder-surface-500 font-mono text-sm
                       focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
            />
            <p className="text-xs text-surface-500 mt-1">
              Get your key from{' '}
              <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer"
                 className="text-primary-400 hover:underline">
                console.anthropic.com
              </a>
            </p>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700">
          <p className="text-xs text-surface-400">
            API keys are stored locally in your browser and are only used when making requests to the AI providers.
            For production use, configure keys via environment variables on the server.
          </p>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSaveApiKeys}
            className="flex items-center gap-2 px-6 py-3 bg-primary-500 text-white font-medium 
                     rounded-lg hover:bg-primary-600 transition-all"
          >
            {saved ? (
              <>
                <Check className="w-5 h-5" />
                Saved!
              </>
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save API Keys
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  )
}
