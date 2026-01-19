import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Code,
  Shield,
  ChevronRight,
  FolderOpen,
  Sparkles,
  Check,
  Loader2,
  AlertCircle,
  Target,
  ChevronDown,
  ChevronUp,
  Layers,
  Users,
  Database,
  Lock,
  Globe,
  Eye,
  FileCheck,
  Key,
  AlertTriangle,
  Upload,
  Code2,
  Network,
  X,
} from 'lucide-react'
import { api } from '../services/api'
import { useBackend } from '../hooks/useBackend'
import type { ParsedIntent, ReviewRequest, CollaborationFeatures } from '../types'

type Step = 'prd' | 'codebase' | 'config' | 'review'

export default function NewReview() {
  const navigate = useNavigate()
  const { isConnected } = useBackend()
  const [step, setStep] = useState<Step>('prd')
  const [prdContent, setPrdContent] = useState('')
  const [prdTitle, setPrdTitle] = useState('')
  const [prdFilePath, setPrdFilePath] = useState<string | null>(null)  // Track file path for save-to-file
  const [codebasePath, setCodebasePath] = useState('')
  const [languages, setLanguages] = useState(['python', 'kotlin', 'typescript'])
  const [useLLM, setUseLLM] = useState(true)
  const [dimensions, setDimensions] = useState<string[]>(['security'])
  const [parsedIntent, setParsedIntent] = useState<ParsedIntent | null>(null)
  const [openaiKey, setOpenaiKey] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')

  // Fetch feature flags to check if save-to-file is enabled
  const { data: features } = useQuery<CollaborationFeatures>({
    queryKey: ['collaboration-features'],
    queryFn: () => api.getCollaborationFeatures(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })
  
  const saveToFileEnabled = features?.prd_save_to_file ?? false

  // Load saved API keys from store
  useEffect(() => {
    const loadKeys = async () => {
      const savedOpenai = await window.electronAPI?.getStore('openaiApiKey')
      const savedAnthropic = await window.electronAPI?.getStore('anthropicApiKey')
      if (savedOpenai) setOpenaiKey(savedOpenai as string)
      if (savedAnthropic) setAnthropicKey(savedAnthropic as string)
    }
    loadKeys()
  }, [])

  // Listen for file/directory selection from menu
  useEffect(() => {
    const cleanupPRD = window.electronAPI?.onPRDLoaded((data) => {
      setPrdContent(data.content)
      setPrdTitle(data.filename.replace(/\.[^/.]+$/, ''))
      setPrdFilePath(data.path)  // Track file path for save-to-file feature
    })

    const cleanupCodebase = window.electronAPI?.onCodebaseSelected((data) => {
      setCodebasePath(data.path)
      if (step === 'prd' && prdContent) {
        setStep('codebase')
      }
    })

    return () => {
      cleanupPRD?.()
      cleanupCodebase?.()
    }
  }, [step, prdContent])

  const createReview = useMutation({
    mutationFn: async () => {
      const request: ReviewRequest = {
        prd: {
          content: prdContent,
          source_type: 'markdown',
          title: prdTitle,
        },
        codebase: {
          path: codebasePath,
          languages,
        },
        config: {
          use_llm: useLLM,
          dimensions,
          compliance_frameworks: ['soc2', 'hipaa', 'pci_dss'],
          openai_api_key: openaiKey || undefined,
          anthropic_api_key: anthropicKey || undefined,
        },
      }
      console.log('Creating review with dimensions:', dimensions)
      console.log('Full request:', JSON.stringify(request, null, 2))
      return api.createReview(request)
    },
    onSuccess: async (data) => {
      // If we have a file path and save-to-file feature is enabled, set it in the backend
      if (prdFilePath && saveToFileEnabled) {
        try {
          const filename = prdFilePath.split('/').pop() || 'PRD.md'
          await api.setPRDFilePath(data.review_id, prdFilePath, filename)
          console.log('PRD file path set for save-to-file:', prdFilePath)
        } catch (err) {
          console.warn('Failed to set PRD file path:', err)
          // Don't block navigation on this error
        }
      }
      
      window.electronAPI?.showNotification(
        'Review Started',
        `Product review "${prdTitle}" has been started.`
      )
      navigate(`/review/${data.review_id}`)
    },
  })

  const parseIntent = useMutation({
    mutationFn: async () => {
      return api.parsePRD(prdContent, prdTitle || 'PRD Analysis')
    },
    onSuccess: (data) => {
      setParsedIntent(data)
      if (data.title && !prdTitle) {
        setPrdTitle(data.title)
      }
    },
  })

  const selectCodebase = async () => {
    const path = await window.electronAPI?.selectDirectory()
    if (path) {
      setCodebasePath(path)
    }
  }

  const selectPRDFile = async () => {
    const path = await window.electronAPI?.selectFile([
      { name: 'Markdown', extensions: ['md', 'markdown'] },
      { name: 'Text', extensions: ['txt'] },
    ])
    if (path) {
      const content = await window.electronAPI?.readFile(path)
      if (content) {
        setPrdContent(content)
        const filename = path.split('/').pop() || ''
        setPrdTitle(filename.replace(/\.[^/.]+$/, ''))
        setPrdFilePath(path)  // Track file path for save-to-file feature
      }
    }
  }

  const steps = [
    { id: 'prd' as Step, label: 'PRD', icon: FileText },
    { id: 'codebase' as Step, label: 'Codebase', icon: Code },
    { id: 'config' as Step, label: 'Config', icon: Sparkles },
    { id: 'review' as Step, label: 'Review', icon: Shield },
  ]

  const currentStepIndex = steps.findIndex((s) => s.id === step)

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-16 h-16 text-ember-400 mb-4" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Backend Required</h2>
        <p className="text-void-400 mb-6">Start the backend server to create reviews.</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">New Product Review</h1>
        <p className="text-void-400 mt-2">Analyze a PRD against your codebase for security concerns</p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between bg-void-900/30 rounded-2xl p-2">
        {steps.map((s, index) => (
          <div key={s.id} className="flex items-center flex-1">
            <button
              onClick={() => index <= currentStepIndex && setStep(s.id)}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-xl transition-all flex-1
                ${step === s.id
                  ? 'bg-neon-500/10 text-neon-400 border border-neon-500/30'
                  : index < currentStepIndex
                    ? 'text-neon-400 hover:bg-void-800'
                    : 'text-void-500'
                }
                ${index <= currentStepIndex ? 'cursor-pointer' : 'cursor-default'}
              `}
            >
              <div
                className={`
                  w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
                  ${step === s.id
                    ? 'bg-neon-500 text-void-950'
                    : index < currentStepIndex
                      ? 'bg-neon-500/20 text-neon-400'
                      : 'bg-void-800 text-void-500'
                  }
                `}
              >
                {index < currentStepIndex ? <Check className="w-5 h-5" /> : <s.icon className="w-5 h-5" />}
              </div>
              <span className="font-medium hidden md:block">{s.label}</span>
            </button>
            {index < steps.length - 1 && (
              <ChevronRight className="w-5 h-5 text-void-600 mx-1 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="card-glass rounded-2xl p-8">
        <AnimatePresence mode="wait">
          {step === 'prd' && (
            <StepPRD
              key="prd"
              content={prdContent}
              title={prdTitle}
              filePath={prdFilePath}
              saveToFileEnabled={saveToFileEnabled}
              parsedIntent={parsedIntent}
              isParsingIntent={parseIntent.isPending}
              parseError={parseIntent.error?.message}
              onContentChange={setPrdContent}
              onTitleChange={setPrdTitle}
              onClearFilePath={() => setPrdFilePath(null)}
              onParseIntent={() => parseIntent.mutate()}
              onSelectFile={selectPRDFile}
              onNext={() => setStep('codebase')}
            />
          )}
          {step === 'codebase' && (
            <StepCodebase
              key="codebase"
              path={codebasePath}
              languages={languages}
              onPathChange={setCodebasePath}
              onLanguagesChange={setLanguages}
              onSelectDirectory={selectCodebase}
              onNext={() => setStep('config')}
              onBack={() => setStep('prd')}
            />
          )}
          {step === 'config' && (
            <StepConfig
              key="config"
              useLLM={useLLM}
              dimensions={dimensions}
              openaiKey={openaiKey}
              anthropicKey={anthropicKey}
              onUseLLMChange={setUseLLM}
              onDimensionsChange={setDimensions}
              onOpenaiKeyChange={setOpenaiKey}
              onAnthropicKeyChange={setAnthropicKey}
              onNext={() => setStep('review')}
              onBack={() => setStep('codebase')}
            />
          )}
          {step === 'review' && (
            <StepReview
              key="review"
              prdTitle={prdTitle}
              codebasePath={codebasePath}
              useLLM={useLLM}
              dimensions={dimensions}
              hasApiKeys={!!(openaiKey.trim() || anthropicKey.trim())}
              parsedIntent={parsedIntent}
              isLoading={createReview.isPending}
              error={createReview.error?.message}
              onSubmit={() => createReview.mutate()}
              onBack={() => setStep('config')}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function StepPRD({
  content,
  title,
  filePath,
  saveToFileEnabled,
  parsedIntent,
  isParsingIntent,
  parseError,
  onContentChange,
  onTitleChange,
  onClearFilePath,
  onParseIntent,
  onSelectFile,
  onNext,
}: {
  content: string
  title: string
  filePath: string | null
  saveToFileEnabled: boolean
  parsedIntent: ParsedIntent | null
  isParsingIntent: boolean
  parseError?: string
  onContentChange: (v: string) => void
  onTitleChange: (v: string) => void
  onClearFilePath: () => void
  onParseIntent: () => void
  onSelectFile: () => void
  onNext: () => void
}) {
  const [showIntentPreview, setShowIntentPreview] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-display font-semibold text-white mb-2">
            Product Requirement Document
          </h2>
          <p className="text-void-400">Paste your PRD content or select a markdown file</p>
        </div>
        <button onClick={onSelectFile} className="btn-secondary flex items-center gap-2">
          <Upload className="w-4 h-4" />
          Select File
        </button>
      </div>
      
      {/* File path indicator - shows when PRD is loaded from a file and save-to-file is enabled */}
      {filePath && saveToFileEnabled && (
        <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-neon-500/10 border border-neon-500/30">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-neon-400" />
            <div>
              <p className="text-sm text-neon-400 font-medium">File loaded</p>
              <p className="text-xs text-neon-300/70 font-mono truncate max-w-md">{filePath}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-neon-300/70">Changes can be saved back to this file</span>
            <button
              onClick={onClearFilePath}
              className="text-neon-400 hover:text-white transition-colors p-1"
              title="Clear file path (paste mode)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-void-300 mb-2">Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="e.g., User Authentication Feature"
          className="input-field"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-void-300 mb-2">PRD Content (Markdown)</label>
        <textarea
          value={content}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder={`# Feature Overview

## Summary
Describe the feature...

## Features
- Feature 1
- Feature 2

## API Changes
- POST /api/users - Create user
- GET /api/users/{id} - Get user

## Security Considerations
- Authentication required
- PII handling`}
          rows={12}
          className="input-field font-mono text-sm resize-none"
        />
      </div>

      {/* Intent Preview Button */}
      {content.trim() && (
        <div className="flex items-center gap-4">
          <button
            onClick={onParseIntent}
            disabled={isParsingIntent}
            className="flex items-center gap-2 px-4 py-2 bg-ember-500/10 border border-ember-500/30
                       text-ember-400 font-medium rounded-xl hover:bg-ember-500/20
                       disabled:opacity-50 transition-all"
          >
            {isParsingIntent ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Target className="w-4 h-4" />
                Preview Intent
              </>
            )}
          </button>

          {parsedIntent && (
            <button
              onClick={() => setShowIntentPreview(!showIntentPreview)}
              className="flex items-center gap-2 text-sm text-void-400 hover:text-white transition-colors"
            >
              {showIntentPreview ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Hide Preview
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Show Preview
                </>
              )}
            </button>
          )}
        </div>
      )}

      {parseError && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Analysis Failed</p>
            <p className="text-sm text-red-300">{parseError}</p>
          </div>
        </div>
      )}

      <AnimatePresence>
        {parsedIntent && showIntentPreview && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <IntentPreviewCard intent={parsedIntent} />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex justify-end pt-4">
        <button onClick={onNext} disabled={!content.trim()} className="btn-primary flex items-center gap-2">
          Continue
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  )
}

function IntentPreviewCard({ intent }: { intent: ParsedIntent }) {
  return (
    <div className="p-5 rounded-xl bg-ember-500/5 border border-ember-500/20 space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-ember-500/20 flex items-center justify-center">
          <Target className="w-5 h-5 text-ember-400" />
        </div>
        <div>
          <h3 className="font-semibold text-white">{intent.title}</h3>
          <p className="text-sm text-void-400">Intent Analysis Preview</p>
        </div>
      </div>

      {intent.summary && <p className="text-sm text-void-300 leading-relaxed">{intent.summary}</p>}

      <div className="grid grid-cols-3 gap-4">
        <IntentStatBox icon={Layers} label="Features" value={intent.features.length} color="neon" />
        <IntentStatBox icon={Code} label="API Changes" value={intent.api_changes.length} color="aurora" />
        <IntentStatBox icon={Database} label="Data Entities" value={intent.data_entities.length} color="ember" />
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="flex items-center gap-2 text-void-400">
          <Users className="w-4 h-4" />
          <span>{intent.user_stories.length} User Stories</span>
        </div>
        <div className="flex items-center gap-2 text-void-400">
          <Lock className="w-4 h-4" />
          <span>{intent.auth_requirements.length} Auth Requirements</span>
        </div>
        <div className="flex items-center gap-2 text-void-400">
          <Globe className="w-4 h-4" />
          <span>{intent.external_integrations.length} Integrations</span>
        </div>
        <div className="flex items-center gap-2 text-red-400">
          <Shield className="w-4 h-4" />
          <span>{intent.data_entities.filter((e) => e.is_sensitive).length} Sensitive Data</span>
        </div>
      </div>
    </div>
  )
}

function IntentStatBox({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Layers
  label: string
  value: number
  color: string
}) {
  const colorClasses: Record<string, string> = {
    neon: 'bg-neon-500/20 text-neon-400 border-neon-500/30',
    aurora: 'bg-aurora-500/20 text-aurora-400 border-aurora-500/30',
    ember: 'bg-ember-500/20 text-ember-400 border-ember-500/30',
  }

  return (
    <div className={`${colorClasses[color]} rounded-xl border p-3 text-center`}>
      <Icon className="w-5 h-5 mx-auto mb-1" />
      <p className="text-lg font-bold text-white">{value}</p>
      <p className="text-xs opacity-80">{label}</p>
    </div>
  )
}

function StepCodebase({
  path,
  languages,
  onPathChange,
  onLanguagesChange,
  onSelectDirectory,
  onNext,
  onBack,
}: {
  path: string
  languages: string[]
  onPathChange: (v: string) => void
  onLanguagesChange: (v: string[]) => void
  onSelectDirectory: () => void
  onNext: () => void
  onBack: () => void
}) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  
  const toggleLanguage = (lang: string) => {
    if (languages.includes(lang)) {
      onLanguagesChange(languages.filter((l) => l !== lang))
    } else {
      onLanguagesChange([...languages, lang])
    }
  }
  
  // Check if input looks like a GitHub URL
  const isGitHubUrl = (input: string) => {
    return input.includes('github.com') || 
           (input.includes('/') && !input.startsWith('/') && input.split('/').length === 2)
  }
  
  // Handle path change - detect GitHub URLs and download automatically
  const handlePathChange = async (newPath: string) => {
    onPathChange(newPath)
    setDownloadError(null)
    
    // If it looks like a GitHub URL, try to download it
    if (isGitHubUrl(newPath) && window.electronAPI?.downloadGitHubRepo) {
      setIsDownloading(true)
      try {
        const downloadedPath = await window.electronAPI.downloadGitHubRepo(newPath)
        onPathChange(downloadedPath)
        setDownloadError(null)
      } catch (err) {
        setDownloadError(err instanceof Error ? err.message : 'Failed to download repository')
      } finally {
        setIsDownloading(false)
      }
    }
  }

  const availableLanguages = [
    { id: 'python', label: 'Python', color: 'text-yellow-400' },
    { id: 'kotlin', label: 'Kotlin', color: 'text-aurora-400' },
    { id: 'typescript', label: 'TypeScript', color: 'text-blue-400' },
    { id: 'javascript', label: 'JavaScript', color: 'text-yellow-300' },
    { id: 'yaml', label: 'YAML/OpenAPI', color: 'text-red-400' },
    { id: 'json', label: 'JSON', color: 'text-green-400' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2">Codebase Configuration</h2>
        <p className="text-void-400">Select your codebase directory and languages to analyze</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-void-300 mb-2">Codebase Path</label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <FolderOpen className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
            <input
              type="text"
              value={path}
              onChange={(e) => handlePathChange(e.target.value)}
              placeholder="/path/to/your/codebase"
              className="input-field pl-12 font-mono text-sm"
              disabled={isDownloading}
            />
            {isDownloading && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 className="w-5 h-5 text-neon-400 animate-spin" />
              </div>
            )}
          </div>
          <button onClick={onSelectDirectory} className="btn-secondary flex items-center gap-2" disabled={isDownloading}>
            <FolderOpen className="w-4 h-4" />
            Browse
          </button>
        </div>
        {isDownloading && (
          <p className="text-xs text-neon-400 mt-2 flex items-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin" />
            Downloading repository from GitHub...
          </p>
        )}
        {downloadError && (
          <p className="text-xs text-red-400 mt-2 flex items-center gap-2">
            <AlertCircle className="w-3 h-3" />
            {downloadError}
          </p>
        )}
        {!isDownloading && !downloadError && (
          <p className="text-xs text-void-500 mt-2">
            You can also enter a GitHub URL (e.g., owner/repo or https://github.com/owner/repo)
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-void-300 mb-3">Languages to Analyze</label>
        <div className="grid grid-cols-3 gap-3">
          {availableLanguages.map((lang) => (
            <button
              key={lang.id}
              onClick={() => toggleLanguage(lang.id)}
              className={`
                px-4 py-3 rounded-xl border font-medium transition-all flex items-center gap-2
                ${languages.includes(lang.id)
                  ? 'bg-neon-500/10 border-neon-500/50 text-neon-400'
                  : 'bg-void-800/50 border-void-700 text-void-400 hover:border-void-600'
                }
              `}
            >
              {languages.includes(lang.id) && <Check className="w-4 h-4" />}
              <span className={languages.includes(lang.id) ? '' : lang.color}>{lang.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <button onClick={onBack} className="text-void-400 hover:text-white transition-colors px-4 py-2">
          Back
        </button>
        <button
          onClick={onNext}
          disabled={!path.trim() || languages.length === 0}
          className="btn-primary flex items-center gap-2"
        >
          Continue
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  )
}

function StepConfig({
  useLLM,
  dimensions,
  openaiKey,
  anthropicKey,
  onUseLLMChange,
  onDimensionsChange,
  onOpenaiKeyChange,
  onAnthropicKeyChange,
  onNext,
  onBack,
}: {
  useLLM: boolean
  dimensions: string[]
  openaiKey: string
  anthropicKey: string
  onUseLLMChange: (v: boolean) => void
  onDimensionsChange: (v: string[]) => void
  onOpenaiKeyChange: (v: string) => void
  onAnthropicKeyChange: (v: string) => void
  onNext: () => void
  onBack: () => void
}) {
  const hasApiKeys = openaiKey.trim() !== '' || anthropicKey.trim() !== ''

  const toggleDimension = (dim: string) => {
    if (dimensions.includes(dim)) {
      if (dimensions.length > 1) {
        onDimensionsChange(dimensions.filter((d) => d !== dim))
      }
    } else {
      onDimensionsChange([...dimensions, dim])
    }
  }

  const dimensionInfo = [
    {
      id: 'security',
      icon: Shield,
      label: 'Security',
      description: 'STRIDE threat modeling, OWASP Top 10',
      color: 'neon',
    },
    {
      id: 'privacy',
      icon: Eye,
      label: 'Privacy',
      description: 'LINDDUN framework, GDPR/CCPA',
      color: 'aurora',
    },
    {
      id: 'compliance',
      icon: FileCheck,
      label: 'Compliance',
      description: 'SOC 2, HIPAA, PCI-DSS, ISO 27001',
      color: 'ember',
    },
    {
      id: 'engineering',
      icon: Code2,
      label: 'Engineering',
      description: 'Code quality, testing, technical debt',
      color: 'yellow',
    },
    {
      id: 'architecture',
      icon: Network,
      label: 'Architecture',
      description: 'API design, dependencies, resilience',
      color: 'purple',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2">Analysis Configuration</h2>
        <p className="text-void-400">Configure how the product review should be performed</p>
      </div>

      {/* Review Dimensions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-void-300">Review Dimensions</label>
          <span className="text-xs text-void-400">
            Selected: <span className="text-neon-400 font-medium">{dimensions.join(', ')}</span>
          </span>
        </div>
        <p className="text-xs text-void-500 mb-3">Click to toggle dimensions. Click a selected dimension to deselect it.</p>
        <div className="grid grid-cols-3 gap-4">
          {dimensionInfo.map((dim) => {
            const Icon = dim.icon
            const isSelected = dimensions.includes(dim.id)
            const colorClasses: Record<string, string> = {
              neon: isSelected ? 'bg-neon-500/10 border-neon-500/50 text-neon-400' : '',
              aurora: isSelected ? 'bg-aurora-500/10 border-aurora-500/50 text-aurora-400' : '',
              ember: isSelected ? 'bg-ember-500/10 border-ember-500/50 text-ember-400' : '',
              yellow: isSelected ? 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400' : '',
              purple: isSelected ? 'bg-purple-500/10 border-purple-500/50 text-purple-400' : '',
            }

            return (
              <button
                key={dim.id}
                onClick={() => toggleDimension(dim.id)}
                disabled={isSelected && dimensions.length === 1}
                className={`
                  p-4 rounded-xl border text-left transition-all
                  ${isSelected
                    ? colorClasses[dim.color]
                    : 'bg-void-800/50 border-void-700 text-void-400 hover:border-void-600'
                  }
                  ${isSelected && dimensions.length === 1 ? 'cursor-not-allowed opacity-60' : ''}
                `}
              >
                <div className="flex items-center gap-3 mb-2">
                  <Icon className="w-5 h-5" />
                  <span className="font-medium text-white">{dim.label}</span>
                  {isSelected && <Check className="w-4 h-4 ml-auto" />}
                </div>
                <p className="text-xs opacity-80">{dim.description}</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* LLM Toggle */}
      <div className="space-y-4">
        <label className="flex items-center justify-between p-4 rounded-xl bg-void-800/50 border border-void-700 cursor-pointer hover:border-void-600 transition-all">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-neon-500/20 to-aurora-500/20 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-neon-400" />
            </div>
            <div>
              <p className="font-medium text-white">AI-Powered Analysis</p>
              <p className="text-sm text-void-400">Use OpenAI + Anthropic for deeper semantic analysis</p>
            </div>
          </div>
          <div className="relative">
            <input
              type="checkbox"
              checked={useLLM}
              onChange={(e) => onUseLLMChange(e.target.checked)}
              className="sr-only"
            />
            <div
              className={`
                w-14 h-8 rounded-full transition-colors
                ${useLLM ? 'bg-neon-500' : 'bg-void-700'}
              `}
            >
              <div
                className={`
                  w-6 h-6 rounded-full bg-white shadow-lg transition-transform mt-1
                  ${useLLM ? 'translate-x-7' : 'translate-x-1'}
                `}
              />
            </div>
          </div>
        </label>

        {/* API Keys */}
        {useLLM && (
          <div className="p-4 rounded-xl bg-void-800/30 border border-void-700 space-y-4">
            <div className="flex items-center gap-3">
              <Key className="w-5 h-5 text-neon-400" />
              <div>
                <p className="font-medium text-white">API Keys</p>
                <p className="text-xs text-void-400">Required for AI-powered analysis</p>
              </div>
            </div>

            {!hasApiKeys && (
              <div className="flex items-start gap-3 p-3 rounded-xl bg-ember-500/10 border border-ember-500/30">
                <AlertTriangle className="w-5 h-5 text-ember-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-ember-400 font-medium">No API keys provided</p>
                  <p className="text-xs text-ember-300/80 mt-0.5">
                    Without API keys, the review will use pattern-based analysis only.
                  </p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-void-400 mb-1.5">OpenAI API Key</label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => onOpenaiKeyChange(e.target.value)}
                  placeholder="sk-..."
                  className="input-field text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-void-400 mb-1.5">Anthropic API Key</label>
                <input
                  type="password"
                  value={anthropicKey}
                  onChange={(e) => onAnthropicKeyChange(e.target.value)}
                  placeholder="sk-ant-..."
                  className="input-field text-sm"
                />
              </div>
            </div>

            {hasApiKeys && (
              <div className="flex items-center gap-2 text-neon-400 text-sm">
                <Check className="w-4 h-4" />
                <span>API key provided - AI analysis enabled</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-between pt-4">
        <button onClick={onBack} className="text-void-400 hover:text-white transition-colors px-4 py-2">
          Back
        </button>
        <button onClick={onNext} className="btn-primary flex items-center gap-2">
          Continue
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  )
}

function StepReview({
  prdTitle,
  codebasePath,
  useLLM,
  dimensions,
  hasApiKeys,
  parsedIntent,
  isLoading,
  error,
  onSubmit,
  onBack,
}: {
  prdTitle: string
  codebasePath: string
  useLLM: boolean
  dimensions: string[]
  hasApiKeys: boolean
  parsedIntent: ParsedIntent | null
  isLoading: boolean
  error?: string
  onSubmit: () => void
  onBack: () => void
}) {
  const dimensionLabels: Record<string, string> = {
    security: 'Security',
    privacy: 'Privacy',
    compliance: 'Compliance',
    engineering: 'Engineering',
    architecture: 'Architecture',
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2">Review Summary</h2>
        <p className="text-void-400">Confirm your configuration and start the product review</p>
      </div>

      <div className="space-y-4">
        <div className="p-4 rounded-xl bg-void-800/50 border border-void-700">
          <div className="flex items-center gap-3 mb-2">
            <FileText className="w-5 h-5 text-neon-400" />
            <span className="font-medium text-white">PRD</span>
          </div>
          <p className="text-void-400 text-sm">{prdTitle || 'Untitled'}</p>
          {parsedIntent && (
            <div className="mt-3 pt-3 border-t border-void-700 flex items-center gap-4 text-xs text-void-500">
              <span className="flex items-center gap-1">
                <Layers className="w-3 h-3" />
                {parsedIntent.features.length} features
              </span>
              <span className="flex items-center gap-1">
                <Code className="w-3 h-3" />
                {parsedIntent.api_changes.length} API changes
              </span>
              <span className="flex items-center gap-1">
                <Database className="w-3 h-3" />
                {parsedIntent.data_entities.length} entities
              </span>
            </div>
          )}
        </div>

        <div className="p-4 rounded-xl bg-void-800/50 border border-void-700">
          <div className="flex items-center gap-3 mb-2">
            <Code className="w-5 h-5 text-neon-400" />
            <span className="font-medium text-white">Codebase</span>
          </div>
          <p className="text-void-400 text-sm font-mono">{codebasePath}</p>
        </div>

        <div className="p-4 rounded-xl bg-void-800/50 border border-void-700">
          <div className="flex items-center gap-3 mb-3">
            <Sparkles className="w-5 h-5 text-neon-400" />
            <span className="font-medium text-white">Analysis</span>
          </div>
          <div className="space-y-2">
            {useLLM && hasApiKeys ? (
              <div className="flex items-center gap-2 text-neon-400 text-sm">
                <Check className="w-4 h-4" />
                <span>AI-powered analysis enabled</span>
              </div>
            ) : useLLM && !hasApiKeys ? (
              <div className="flex items-center gap-2 text-ember-400 text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>LLM enabled but no API keys - will use pattern-based</span>
              </div>
            ) : (
              <p className="text-void-400 text-sm">Pattern-based analysis only</p>
            )}
            <div className="flex flex-wrap gap-2 mt-2">
              {dimensions.map((dim) => (
                <span
                  key={dim}
                  className="px-3 py-1 text-xs rounded-lg bg-neon-500/10 text-neon-400 border border-neon-500/30"
                >
                  {dimensionLabels[dim] || dim}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Error</p>
            <p className="text-sm text-red-300">{error}</p>
          </div>
        </div>
      )}

      <div className="flex justify-between pt-4">
        <button
          onClick={onBack}
          disabled={isLoading}
          className="text-void-400 hover:text-white transition-colors px-4 py-2 disabled:opacity-50"
        >
          Back
        </button>
        <button onClick={onSubmit} disabled={isLoading} className="btn-primary flex items-center gap-2">
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Starting Review...
            </>
          ) : (
            <>
              <Shield className="w-5 h-5" />
              Start Product Review
            </>
          )}
        </button>
      </div>
    </motion.div>
  )
}

