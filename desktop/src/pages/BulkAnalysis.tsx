import { useState, useCallback } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Code,
  Shield,
  Sparkles,
  Check,
  Loader2,
  AlertCircle,
  Upload,
  X,
  FolderOpen,
  Layers,
  ChevronRight,
  PlayCircle,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  TrendingUp,
  Star,
} from 'lucide-react'
import { api } from '../services/api'
import type { BulkPRDFile, BulkAnalysisResult, SinglePRDResult } from '../types'

interface UploadedFile {
  id: string
  file: File
  name: string
  content: string
  status: 'pending' | 'reading' | 'ready' | 'error'
  error?: string
}

export default function BulkAnalysis() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [codebasePath, setCodebasePath] = useState('')
  const [dimensions, setDimensions] = useState<string[]>(['security', 'privacy', 'compliance', 'engineering', 'architecture'])
  const [useLLM, setUseLLM] = useState(true)
  const [result, setResult] = useState<BulkAnalysisResult | null>(null)

  // Fetch config to check if feature is enabled
  const { data: config, isLoading: configLoading, error: configError } = useQuery({
    queryKey: ['bulk-config'],
    queryFn: () => api.getBulkAnalysisConfig(),
  })

  // Mutation for running bulk analysis
  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const prds: BulkPRDFile[] = files
        .filter(f => f.status === 'ready')
        .map(f => ({
          file_name: f.name,
          content: f.content,
          codebase_path: codebasePath || null,
          dimensions: dimensions,
        }))

      return api.analyzeBulkPRDs({
        prds,
        default_codebase_path: codebasePath || null,
        default_dimensions: dimensions,
        use_llm: useLLM,
        use_pattern_matching: true,
      })
    },
    onSuccess: (data) => {
      setResult(data)
    },
  })

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const droppedFiles = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.md'))
    addFiles(droppedFiles)
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter(f => f.name.endsWith('.md'))
      addFiles(selectedFiles)
    }
  }, [])

  // Handle folder selection via Electron
  const handleFolderSelect = async () => {
    if (window.electronAPI?.selectDirectory) {
      const folderPath = await window.electronAPI.selectDirectory()
      if (folderPath) {
        setCodebasePath(folderPath)
      }
    }
  }

  const addFiles = async (newFiles: File[]) => {
    const maxFiles = config?.max_files || 20
    const remainingSlots = maxFiles - files.length
    const filesToAdd = newFiles.slice(0, remainingSlots)

    const uploadedFiles: UploadedFile[] = filesToAdd.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      name: file.name,
      content: '',
      status: 'reading' as const,
    }))

    setFiles(prev => [...prev, ...uploadedFiles])

    // Read file contents
    for (const uf of uploadedFiles) {
      try {
        const content = await readFileContent(uf.file)
        setFiles(prev => prev.map(f => 
          f.id === uf.id ? { ...f, content, status: 'ready' as const } : f
        ))
      } catch (err) {
        setFiles(prev => prev.map(f => 
          f.id === uf.id ? { ...f, status: 'error' as const, error: 'Failed to read file' } : f
        ))
      }
    }
  }

  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = reject
      reader.readAsText(file)
    })
  }

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const toggleDimension = (dim: string) => {
    if (dimensions.includes(dim)) {
      if (dimensions.length > 1) {
        setDimensions(dimensions.filter(d => d !== dim))
      }
    } else {
      setDimensions([...dimensions, dim])
    }
  }

  const readyFiles = files.filter(f => f.status === 'ready')
  const canAnalyze = readyFiles.length > 0 && !analyzeMutation.isPending

  // Show results if available - check this FIRST to prevent blank screen during config refetch
  if (result) {
    return <BulkAnalysisResults result={result} onBack={() => setResult(null)} />
  }

  // Feature not enabled
  if (configError || (config && !config.enabled)) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-8 text-center">
          <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Bulk Analysis Not Enabled</h2>
          <p className="text-void-400 mb-4">
            Set <code className="text-amber-400 bg-void-900 px-2 py-1 rounded">FEATURE_BULK_PRD_ANALYSIS=true</code> to enable this feature.
          </p>
          <button
            onClick={() => navigate('/settings')}
            className="px-4 py-2 bg-void-800 border border-void-700 text-void-300 rounded-lg hover:border-neon-500/50 transition-colors"
          >
            Go to Settings
          </button>
        </div>
      </div>
    )
  }

  if (configLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-neon-400 animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white flex items-center gap-3">
          <Layers className="w-8 h-8 text-neon-400" />
          Bulk PRD Analysis
        </h1>
        <p className="text-void-400 mt-1">
          Analyze up to {config?.max_files || 20} PRD files in parallel across multiple review dimensions
        </p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={FileText}
          label="PRD Files"
          value={`${readyFiles.length}/${config?.max_files || 20}`}
          color="neon"
        />
        <StatCard
          icon={Layers}
          label="Dimensions"
          value={dimensions.length.toString()}
          color="purple"
        />
        <StatCard
          icon={Sparkles}
          label="Parallel Workers"
          value={(config?.max_parallel_reviews || 20).toString()}
          color="cyan"
        />
        <StatCard
          icon={Star}
          label="Smart Default"
          value={config?.smart_codebase_default_enabled ? 'On' : 'Off'}
          color="amber"
        />
      </div>

      {/* File Upload Area */}
      <div className="bg-void-900/50 backdrop-blur-sm rounded-2xl border border-void-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Upload className="w-5 h-5 text-neon-400" />
          Upload PRD Files
        </h2>

        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-void-700 rounded-xl p-8 text-center hover:border-neon-500/50 transition-colors"
        >
          <Upload className="w-12 h-12 text-void-500 mx-auto mb-4" />
          <p className="text-void-300 mb-2">
            Drag & drop PRD files here, or click to select
          </p>
          <p className="text-void-500 text-sm mb-4">
            Supports .md files (max {config?.max_files || 20} files)
          </p>
          <input
            type="file"
            multiple
            accept=".md"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <label
            htmlFor="file-input"
            className="inline-flex items-center gap-2 px-4 py-2 bg-neon-500/20 border border-neon-500/30 text-neon-400 rounded-lg cursor-pointer hover:bg-neon-500/30 transition-colors"
          >
            <FileText className="w-4 h-4" />
            Select Files
          </label>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-void-400">
                {readyFiles.length} file{readyFiles.length !== 1 ? 's' : ''} ready
              </span>
              {files.length > 0 && (
                <button
                  onClick={() => setFiles([])}
                  className="text-sm text-red-400 hover:text-red-300 transition-colors"
                >
                  Clear all
                </button>
              )}
            </div>
            <div className="max-h-48 overflow-y-auto space-y-2">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 bg-void-800 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {file.status === 'reading' && (
                      <Loader2 className="w-4 h-4 text-neon-400 animate-spin" />
                    )}
                    {file.status === 'ready' && (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    )}
                    {file.status === 'error' && (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <FileText className="w-4 h-4 text-void-400" />
                    <span className="text-white text-sm">{file.name}</span>
                  </div>
                  <button
                    onClick={() => removeFile(file.id)}
                    className="p-1 text-void-500 hover:text-red-400 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Configuration */}
      <div className="grid grid-cols-2 gap-6">
        {/* Codebase */}
        <div className="bg-void-900/50 backdrop-blur-sm rounded-2xl border border-void-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Code className="w-5 h-5 text-neon-400" />
            Codebase
          </h2>

          {config?.current_default_codebase && (
            <div className="mb-4 p-3 bg-neon-500/10 border border-neon-500/30 rounded-lg">
              <p className="text-sm text-neon-400 flex items-center gap-2">
                <Star className="w-4 h-4" />
                Smart default available
              </p>
              <p className="text-xs text-void-400 mt-1 truncate">
                {config.current_default_codebase}
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <div className="relative flex-1">
              <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
              <input
                type="text"
                value={codebasePath}
                onChange={(e) => setCodebasePath(e.target.value)}
                placeholder={config?.current_default_codebase || "/path/to/codebase"}
                className="w-full pl-10 pr-4 py-3 bg-void-800 border border-void-700 rounded-lg text-white placeholder-void-500 focus:border-neon-500 focus:ring-1 focus:ring-neon-500 transition-all text-sm"
              />
            </div>
            <button
              onClick={handleFolderSelect}
              className="px-4 py-3 bg-void-800 border border-void-700 text-void-400 rounded-lg hover:border-neon-500/50 hover:text-neon-400 transition-colors"
            >
              <FolderOpen className="w-5 h-5" />
            </button>
          </div>

          {/* Codebase suggestions */}
          {config?.codebase_suggestions && config.codebase_suggestions.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-void-500 mb-2">Recent codebases:</p>
              <div className="space-y-1">
                {config.codebase_suggestions.slice(0, 3).map((suggestion) => (
                  <button
                    key={suggestion.path}
                    onClick={() => setCodebasePath(suggestion.path)}
                    className="w-full text-left p-2 text-xs bg-void-800 hover:bg-void-700 rounded-lg transition-colors flex items-center justify-between group"
                  >
                    <span className="text-void-300 truncate">{suggestion.name}</span>
                    <span className="text-void-500 group-hover:text-neon-400">
                      {suggestion.selection_count}x
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Dimensions */}
        <div className="bg-void-900/50 backdrop-blur-sm rounded-2xl border border-void-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-neon-400" />
            Review Dimensions
          </h2>

          <div className="space-y-2">
            {[
              { id: 'security', label: 'Security', color: 'neon' },
              { id: 'privacy', label: 'Privacy', color: 'purple' },
              { id: 'compliance', label: 'Compliance', color: 'blue' },
              { id: 'engineering', label: 'Engineering', color: 'green' },
              { id: 'architecture', label: 'Architecture', color: 'orange' },
            ].map((dim) => (
              <button
                key={dim.id}
                onClick={() => toggleDimension(dim.id)}
                disabled={dimensions.includes(dim.id) && dimensions.length === 1}
                className={`
                  w-full flex items-center justify-between p-3 rounded-lg border transition-all
                  ${dimensions.includes(dim.id)
                    ? 'bg-neon-500/20 border-neon-500/50 text-neon-400'
                    : 'bg-void-800 border-void-700 text-void-400 hover:border-void-600'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                <span className="font-medium">{dim.label}</span>
                {dimensions.includes(dim.id) && <Check className="w-4 h-4" />}
              </button>
            ))}
          </div>

          {/* LLM Toggle */}
          <div className="mt-4 pt-4 border-t border-void-700">
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-neon-400" />
                <span className="text-sm text-white">LLM Analysis</span>
              </div>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={useLLM}
                  onChange={(e) => setUseLLM(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-10 h-6 rounded-full transition-colors ${useLLM ? 'bg-neon-500' : 'bg-void-700'}`}>
                  <div className={`w-4 h-4 rounded-full bg-white shadow transition-transform mt-1 ${useLLM ? 'translate-x-5' : 'translate-x-1'}`} />
                </div>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Error */}
      {analyzeMutation.error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Analysis Failed</p>
            <p className="text-sm text-red-300">{analyzeMutation.error.message}</p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <button
          onClick={() => navigate('/new')}
          className="px-6 py-3 text-void-400 hover:text-white transition-colors"
        >
          Single Analysis
        </button>
        <button
          onClick={() => analyzeMutation.mutate()}
          disabled={!canAnalyze}
          className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-neon-500 to-accent-500 text-void-950 font-medium rounded-lg hover:from-neon-400 hover:to-accent-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-neon-500/25"
        >
          {analyzeMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Analyzing {readyFiles.length} PRDs...
            </>
          ) : (
            <>
              <PlayCircle className="w-5 h-5" />
              Analyze {readyFiles.length} PRDs
            </>
          )}
        </button>
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: typeof FileText
  label: string
  value: string
  color: string
}) {
  const colorClasses: Record<string, string> = {
    neon: 'bg-neon-500/10 border-neon-500/30 text-neon-400',
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
    cyan: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
  }

  return (
    <div className={`${colorClasses[color]} border rounded-xl p-4`}>
      <Icon className="w-5 h-5 mb-2" />
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs opacity-80">{label}</p>
    </div>
  )
}

function BulkAnalysisResults({ result, onBack }: { result: BulkAnalysisResult; onBack: () => void }) {
  const navigate = useNavigate()

  const severityColors: Record<string, string> = {
    critical: 'text-red-400',
    high: 'text-orange-400',
    medium: 'text-amber-400',
    low: 'text-blue-400',
    info: 'text-void-400',
  }

  const dimensionColors: Record<string, string> = {
    security: 'text-neon-400',
    privacy: 'text-purple-400',
    compliance: 'text-blue-400',
    engineering: 'text-green-400',
    architecture: 'text-orange-400',
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-neon-400" />
            Bulk Analysis Results
          </h1>
          <p className="text-void-400 mt-1">
            Analyzed {result.total_prds ?? 0} PRD files in {((result.total_duration_ms ?? 0) / 1000).toFixed(1)}s
          </p>
        </div>
        <button
          onClick={onBack}
          className="px-4 py-2 text-void-400 hover:text-white transition-colors"
        >
          ← New Analysis
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-void-900/50 border border-void-800 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-white">{result.total_prds ?? 0}</p>
          <p className="text-xs text-void-400">Total PRDs</p>
        </div>
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">{result.successful_prds ?? 0}</p>
          <p className="text-xs text-green-400/80">Successful</p>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-red-400">{result.failed_prds ?? 0}</p>
          <p className="text-xs text-red-400/80">Failed</p>
        </div>
        <div className="bg-neon-500/10 border border-neon-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-neon-400">{result.total_findings ?? 0}</p>
          <p className="text-xs text-neon-400/80">Total Findings</p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-amber-400">{(result.success_rate ?? 0).toFixed(0)}%</p>
          <p className="text-xs text-amber-400/80">Success Rate</p>
        </div>
      </div>

      {/* Findings Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        {/* By Severity */}
        <div className="bg-void-900/50 border border-void-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-neon-400" />
            Findings by Severity
          </h3>
          <div className="space-y-3">
            {Object.entries(result.findings_by_severity ?? {}).map(([severity, count]) => (
              <div key={severity} className="flex items-center justify-between">
                <span className={`capitalize ${severityColors[severity] || 'text-void-400'}`}>
                  {severity}
                </span>
                <span className="text-white font-medium">{count}</span>
              </div>
            ))}
            {Object.keys(result.findings_by_severity ?? {}).length === 0 && (
              <p className="text-void-500 text-sm">No findings</p>
            )}
          </div>
        </div>

        {/* By Dimension */}
        <div className="bg-void-900/50 border border-void-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-neon-400" />
            Findings by Dimension
          </h3>
          <div className="space-y-3">
            {Object.entries(result.findings_by_dimension ?? {}).map(([dimension, count]) => (
              <div key={dimension} className="flex items-center justify-between">
                <span className={`capitalize ${dimensionColors[dimension] || 'text-void-400'}`}>
                  {dimension}
                </span>
                <span className="text-white font-medium">{count}</span>
              </div>
            ))}
            {Object.keys(result.findings_by_dimension ?? {}).length === 0 && (
              <p className="text-void-500 text-sm">No findings</p>
            )}
          </div>
        </div>
      </div>

      {/* Individual Results */}
      <div className="bg-void-900/50 border border-void-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-neon-400" />
          Individual PRD Results
        </h3>
        <div className="space-y-3">
          {(result.prd_results ?? []).map((prdResult) => (
            <PRDResultCard
              key={prdResult.prd_id}
              result={prdResult}
              onViewDetails={() => {
                if (prdResult.review_id) {
                  navigate(`/review/${prdResult.review_id}`)
                }
              }}
            />
          ))}
        </div>
      </div>

      {/* Metadata */}
      <div className="text-xs text-void-500 flex items-center gap-4">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {((result.total_duration_ms ?? 0) / 1000).toFixed(2)}s total
        </span>
        <span className="flex items-center gap-1">
          <Sparkles className="w-3 h-3" />
          {result.parallel_workers_used ?? 1} parallel workers
        </span>
        {result.default_codebase && (
          <span className="flex items-center gap-1">
            <Star className="w-3 h-3" />
            Default: {result.default_codebase.split('/').pop()}
          </span>
        )}
      </div>
    </div>
  )
}

function PRDResultCard({ result, onViewDetails }: { result: SinglePRDResult; onViewDetails: () => void }) {
  return (
    <div className={`
      flex items-center justify-between p-4 rounded-lg border transition-all
      ${result.success 
        ? 'bg-void-800 border-void-700 hover:border-void-600' 
        : 'bg-red-500/10 border-red-500/30'
      }
    `}>
      <div className="flex items-center gap-4">
        {result.success ? (
          <CheckCircle className="w-5 h-5 text-green-400" />
        ) : (
          <XCircle className="w-5 h-5 text-red-400" />
        )}
        <div>
          <p className="text-white font-medium">{result.prd_file_name}</p>
          {result.success ? (
            <p className="text-xs text-void-400">
              {result.total_findings} findings • {(result.duration_ms / 1000).toFixed(2)}s
            </p>
          ) : (
            <p className="text-xs text-red-400">{result.error_message}</p>
          )}
        </div>
      </div>
      {result.success && result.review_id && (
        <button
          onClick={onViewDetails}
          className="flex items-center gap-1 px-3 py-1.5 text-sm text-neon-400 hover:text-neon-300 transition-colors"
        >
          View Details
          <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}
