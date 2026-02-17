import { useState, useCallback, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  FolderOpen,
  Upload,
  Trash2,
  Play,
  Loader2,
  Check,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Shield,
  Eye,
  FileCheck,
  Code,
  Layers,
  Sparkles,
  X,
  Plus,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import TraceLogPanel from '../components/TraceLogPanel'

interface PRDFile {
  id: string
  fileName: string
  content: string
  codebasePath?: string
  status: 'pending' | 'analyzing' | 'completed' | 'failed'
  error?: string
}

interface BulkAnalysisResult {
  id: string
  totalPrds: number
  successfulPrds: number
  failedPrds: number
  totalFindings: number
  findingsBySeverity: Record<string, number>
  findingsByDimension: Record<string, number>
  prdResults: Array<{
    prdId: string
    prdFileName: string
    success: boolean
    totalFindings: number
    reviewId: string
    errorMessage?: string
    durationMs: number
  }>
  totalDurationMs: number
}

export default function BulkAnalysis() {
  const navigate = useNavigate()
  const [prdFiles, setPrdFiles] = useState<PRDFile[]>([])
  const [defaultCodebasePath, setDefaultCodebasePath] = useState('')
  const [dimensions, setDimensions] = useState<string[]>(['security', 'privacy', 'compliance', 'engineering', 'architecture'])
  const [useLLM, setUseLLM] = useState(true)
  const [openaiKey, setOpenaiKey] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [showConfig, setShowConfig] = useState(false)
  const [result, setResult] = useState<BulkAnalysisResult | null>(null)
  const traceIdRef = useRef<string>('')

  const addPRDFile = useCallback((fileName: string, content: string) => {
    const id = `prd-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    setPrdFiles(prev => [...prev, {
      id,
      fileName,
      content,
      codebasePath: defaultCodebasePath || undefined,
      status: 'pending',
    }])
  }, [defaultCodebasePath])

  const removePRDFile = useCallback((id: string) => {
    setPrdFiles(prev => prev.filter(f => f.id !== id))
  }, [])

  const updatePRDCodebase = useCallback((id: string, codebasePath: string) => {
    setPrdFiles(prev => prev.map(f => 
      f.id === id ? { ...f, codebasePath } : f
    ))
  }, [])

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      if (file.name.endsWith('.md') || file.name.endsWith('.txt')) {
        const reader = new FileReader()
        reader.onload = (event) => {
          const content = event.target?.result as string
          addPRDFile(file.name, content)
        }
        reader.readAsText(file)
      }
    })

    // Reset input
    e.target.value = ''
  }, [addPRDFile])

  const bulkAnalyze = useMutation({
    mutationFn: async () => {
      // Generate a trace_id so the SSE connection can start immediately
      traceIdRef.current = `bulk-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
      const traceId = traceIdRef.current

      const res = await fetch(`/api/bulk/analyze?trace_id=${encodeURIComponent(traceId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prds: prdFiles.map(f => ({
            file_path: f.fileName,
            file_name: f.fileName,
            content: f.content,
            codebase_path: f.codebasePath || defaultCodebasePath || null,
          })),
          default_codebase_path: defaultCodebasePath || null,
          dimensions,
          use_llm: useLLM,
          openai_api_key: openaiKey || undefined,
          anthropic_api_key: anthropicKey || undefined,
        }),
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to start bulk analysis')
      }
      return res.json()
    },
    onSuccess: (data) => {
      setResult(data)
      // Update PRD statuses based on results
      setPrdFiles(prev => prev.map(f => {
        const prdResult = data.prd_results?.find((r: any) => 
          r.prd_file_name === f.fileName || r.prd_id === f.id
        )
        if (prdResult) {
          return {
            ...f,
            status: prdResult.success ? 'completed' : 'failed',
            error: prdResult.error_message,
          }
        }
        return f
      }))
    },
    onError: () => {
      setPrdFiles(prev => prev.map(f => ({ ...f, status: 'failed' })))
    },
  })

  const toggleDimension = (dim: string) => {
    if (dimensions.includes(dim)) {
      if (dimensions.length > 1) {
        setDimensions(dimensions.filter(d => d !== dim))
      }
    } else {
      setDimensions([...dimensions, dim])
    }
  }

  const dimensionInfo = {
    security: { icon: Shield, label: 'Security', color: 'primary' },
    privacy: { icon: Eye, label: 'Privacy', color: 'purple' },
    compliance: { icon: FileCheck, label: 'Compliance', color: 'blue' },
    engineering: { icon: Code, label: 'Engineering', color: 'green' },
    architecture: { icon: Layers, label: 'Architecture', color: 'orange' },
  }

  const hasApiKeys = openaiKey.trim() !== '' || anthropicKey.trim() !== ''

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">
          Bulk PRD Analysis
        </h1>
        <p className="text-surface-400 mt-1">
          Analyze multiple PRD files in parallel across your codebase
        </p>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - PRD Files */}
        <div className="lg:col-span-2 space-y-4">
          {/* Upload Area */}
          <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">PRD Files</h2>
              <span className="text-sm text-surface-400">
                {prdFiles.length}/20 files
              </span>
            </div>

            {/* Drop Zone */}
            <label className="block">
              <div className="border-2 border-dashed border-surface-700 rounded-xl p-8 text-center 
                            hover:border-primary-500/50 hover:bg-surface-800/50 transition-all cursor-pointer">
                <Upload className="w-10 h-10 text-surface-500 mx-auto mb-3" />
                <p className="text-surface-300 font-medium">
                  Drop PRD files here or click to upload
                </p>
                <p className="text-sm text-surface-500 mt-1">
                  Supports .md and .txt files (max 20 files)
                </p>
                <input
                  type="file"
                  multiple
                  accept=".md,.txt"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={prdFiles.length >= 20}
                />
              </div>
            </label>

            {/* File List */}
            {prdFiles.length > 0 && (
              <div className="mt-4 space-y-2">
                {prdFiles.map((file) => (
                  <motion.div
                    key={file.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="flex items-center gap-3 p-3 bg-surface-800 rounded-lg border border-surface-700"
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      file.status === 'completed' ? 'bg-green-500/20' :
                      file.status === 'failed' ? 'bg-red-500/20' :
                      file.status === 'analyzing' ? 'bg-primary-500/20' :
                      'bg-surface-700'
                    }`}>
                      {file.status === 'completed' ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : file.status === 'failed' ? (
                        <XCircle className="w-4 h-4 text-red-400" />
                      ) : file.status === 'analyzing' ? (
                        <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
                      ) : (
                        <FileText className="w-4 h-4 text-surface-400" />
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{file.fileName}</p>
                      <p className="text-xs text-surface-500 truncate">
                        {file.codebasePath || defaultCodebasePath || 'No codebase selected'}
                      </p>
                      {file.error && (
                        <p className="text-xs text-red-400 mt-1">{file.error}</p>
                      )}
                    </div>

                    <input
                      type="text"
                      placeholder="Codebase path"
                      value={file.codebasePath || ''}
                      onChange={(e) => updatePRDCodebase(file.id, e.target.value)}
                      className="w-48 px-2 py-1 text-xs bg-surface-900 border border-surface-700 rounded
                               text-white placeholder-surface-500 focus:border-primary-500 transition-all"
                    />

                    <button
                      onClick={() => removePRDFile(file.id)}
                      className="p-1.5 text-surface-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Results */}
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6"
            >
              <h2 className="text-lg font-semibold text-white mb-4">Analysis Results</h2>
              
              {/* Summary Stats */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-surface-800 rounded-lg text-center">
                  <p className="text-2xl font-bold text-white">{result.totalPrds}</p>
                  <p className="text-xs text-surface-400">Total PRDs</p>
                </div>
                <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                  <p className="text-2xl font-bold text-green-400">{result.successfulPrds}</p>
                  <p className="text-xs text-green-400/80">Successful</p>
                </div>
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-center">
                  <p className="text-2xl font-bold text-red-400">{result.failedPrds}</p>
                  <p className="text-xs text-red-400/80">Failed</p>
                </div>
                <div className="p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg text-center">
                  <p className="text-2xl font-bold text-primary-400">{result.totalFindings}</p>
                  <p className="text-xs text-primary-400/80">Total Findings</p>
                </div>
              </div>

              {/* Findings by Severity */}
              {result.findingsBySeverity && Object.keys(result.findingsBySeverity).length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-surface-300 mb-2">By Severity</h3>
                  <div className="flex gap-2 flex-wrap">
                    {Object.entries(result.findingsBySeverity).map(([severity, count]) => (
                      <span
                        key={severity}
                        className={`px-2 py-1 text-xs rounded ${
                          severity === 'critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                          severity === 'high' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                          severity === 'medium' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                          'bg-surface-700 text-surface-300'
                        }`}
                      >
                        {severity}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Individual Results */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-surface-300 mb-2">Individual Results</h3>
                {result.prdResults?.map((prdResult) => (
                  <div
                    key={prdResult.prdId}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      prdResult.success
                        ? 'bg-green-500/5 border-green-500/20'
                        : 'bg-red-500/5 border-red-500/20'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {prdResult.success ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                      <div>
                        <p className="text-sm text-white">{prdResult.prdFileName}</p>
                        {prdResult.success ? (
                          <p className="text-xs text-surface-400">
                            {prdResult.totalFindings} findings • {(prdResult.durationMs / 1000).toFixed(1)}s
                          </p>
                        ) : (
                          <p className="text-xs text-red-400">{prdResult.errorMessage}</p>
                        )}
                      </div>
                    </div>
                    {prdResult.success && prdResult.reviewId && (
                      <button
                        onClick={() => navigate(`/review/${prdResult.reviewId}`)}
                        className="px-3 py-1 text-xs bg-primary-500/20 text-primary-400 rounded hover:bg-primary-500/30 transition-colors"
                      >
                        View
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-4 text-xs text-surface-500 text-right">
                Total time: {(result.totalDurationMs / 1000).toFixed(1)}s
              </div>
            </motion.div>
          )}
        </div>

        {/* Right Column - Configuration */}
        <div className="space-y-4">
          {/* Default Codebase */}
          <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Default Codebase</h2>
            <div className="relative">
              <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
              <input
                type="text"
                value={defaultCodebasePath}
                onChange={(e) => setDefaultCodebasePath(e.target.value)}
                placeholder="/path/to/codebase"
                className="w-full pl-10 pr-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg
                         text-white placeholder-surface-500 text-sm
                         focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
              />
            </div>
            <p className="text-xs text-surface-500 mt-2">
              Used for PRDs without a specific codebase path
            </p>
          </div>

          {/* Dimensions */}
          <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Analysis Dimensions</h2>
            <div className="space-y-2">
              {(Object.keys(dimensionInfo) as Array<keyof typeof dimensionInfo>).map((dim) => {
                const info = dimensionInfo[dim]
                const Icon = info.icon
                const isSelected = dimensions.includes(dim)
                
                return (
                  <button
                    key={dim}
                    onClick={() => toggleDimension(dim)}
                    disabled={isSelected && dimensions.length === 1}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'bg-primary-500/10 border-primary-500/30 text-white'
                        : 'bg-surface-800 border-surface-700 text-surface-400 hover:border-surface-600'
                    } ${isSelected && dimensions.length === 1 ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    <Icon className={`w-4 h-4 ${isSelected ? 'text-primary-400' : ''}`} />
                    <span className="flex-1 text-sm">{info.label}</span>
                    {isSelected && <Check className="w-4 h-4 text-primary-400" />}
                  </button>
                )
              })}
            </div>
          </div>

          {/* LLM Configuration */}
          <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-6">
            <button
              onClick={() => setShowConfig(!showConfig)}
              className="w-full flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-primary-400" />
                <span className="font-semibold text-white">AI Configuration</span>
              </div>
              {showConfig ? (
                <ChevronUp className="w-5 h-5 text-surface-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-surface-400" />
              )}
            </button>

            <AnimatePresence>
              {showConfig && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-4 space-y-4">
                    {/* LLM Toggle */}
                    <label className="flex items-center justify-between cursor-pointer">
                      <span className="text-sm text-surface-300">Use LLM Analysis</span>
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={useLLM}
                          onChange={(e) => setUseLLM(e.target.checked)}
                          className="sr-only"
                        />
                        <div className={`w-10 h-6 rounded-full transition-colors ${
                          useLLM ? 'bg-primary-500' : 'bg-surface-700'
                        }`}>
                          <div className={`w-4 h-4 rounded-full bg-white shadow-lg transition-transform mt-1 ${
                            useLLM ? 'translate-x-5' : 'translate-x-1'
                          }`} />
                        </div>
                      </div>
                    </label>

                    {useLLM && (
                      <>
                        {!hasApiKeys && (
                          <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                            <p className="text-xs text-amber-400">
                              No API keys provided. Will use pattern-based analysis only.
                            </p>
                          </div>
                        )}

                        <div>
                          <label className="block text-xs text-surface-400 mb-1">OpenAI API Key</label>
                          <input
                            type="password"
                            value={openaiKey}
                            onChange={(e) => setOpenaiKey(e.target.value)}
                            placeholder="sk-..."
                            className="w-full px-3 py-2 text-sm bg-surface-800 border border-surface-700 rounded-lg
                                     text-white placeholder-surface-500 focus:border-primary-500 transition-all"
                          />
                        </div>

                        <div>
                          <label className="block text-xs text-surface-400 mb-1">Anthropic API Key</label>
                          <input
                            type="password"
                            value={anthropicKey}
                            onChange={(e) => setAnthropicKey(e.target.value)}
                            placeholder="sk-ant-..."
                            className="w-full px-3 py-2 text-sm bg-surface-800 border border-surface-700 rounded-lg
                                     text-white placeholder-surface-500 focus:border-primary-500 transition-all"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Start Button */}
          <button
            onClick={() => bulkAnalyze.mutate()}
            disabled={prdFiles.length === 0 || bulkAnalyze.isPending}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 
                     bg-gradient-to-r from-primary-500 to-accent-500 text-white font-medium 
                     rounded-xl hover:from-primary-600 hover:to-accent-600 
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all glow-primary"
          >
            {bulkAnalyze.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing {prdFiles.length} PRDs...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Start Bulk Analysis
              </>
            )}
          </button>

          {bulkAnalyze.error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-400">{bulkAnalyze.error.message}</p>
            </div>
          )}

          {/* Trace log panel — visible while analyzing or after completion */}
          {(bulkAnalyze.isPending || result) && traceIdRef.current && (
            <TraceLogPanel
              traceId={traceIdRef.current}
              endpoint={`/api/bulk/traces/${traceIdRef.current}`}
              isRunning={bulkAnalyze.isPending}
            />
          )}
        </div>
      </div>
    </div>
  )
}
