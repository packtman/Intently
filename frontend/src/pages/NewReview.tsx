import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
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
} from 'lucide-react'

type Step = 'prd' | 'codebase' | 'config' | 'review'

interface ParsedIntent {
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

export default function NewReview() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('prd')
  const [prdContent, setPrdContent] = useState('')
  const [prdTitle, setPrdTitle] = useState('')
  const [codebasePath, setCodebasePath] = useState('')
  const [languages, setLanguages] = useState(['python', 'kotlin'])
  const [useLLM, setUseLLM] = useState(true)
  const [dimensions, setDimensions] = useState<string[]>(['security'])
  const [parsedIntent, setParsedIntent] = useState<ParsedIntent | null>(null)
  const [openaiKey, setOpenaiKey] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')

  const createReview = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
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
            dimensions: dimensions,
            openai_api_key: openaiKey || undefined,
            anthropic_api_key: anthropicKey || undefined,
          },
        }),
      })
      if (!res.ok) throw new Error('Failed to create review')
      return res.json()
    },
    onSuccess: (data) => {
      navigate(`/review/${data.review_id}`)
    },
  })

  const parseIntent = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/parse-prd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: prdContent,
          source_type: 'markdown',
          title: prdTitle || 'PRD Analysis',
        }),
      })
      if (!res.ok) throw new Error('Failed to parse PRD')
      return res.json()
    },
    onSuccess: (data) => {
      setParsedIntent(data)
      if (data.title && !prdTitle) {
        setPrdTitle(data.title)
      }
    },
  })

  const steps = [
    { id: 'prd', label: 'PRD', icon: FileText },
    { id: 'codebase', label: 'Codebase', icon: Code },
    { id: 'config', label: 'Config', icon: Sparkles },
    { id: 'review', label: 'Review', icon: Shield },
  ]

  const currentStepIndex = steps.findIndex(s => s.id === step)

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">
          New Product Review
        </h1>
        <p className="text-surface-400 mt-1">
          Analyze a PRD against your codebase for security concerns
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between">
        {steps.map((s, index) => (
          <div key={s.id} className="flex items-center">
            <button
              onClick={() => index <= currentStepIndex && setStep(s.id as Step)}
              className={`
                flex items-center gap-3 px-4 py-2 rounded-lg transition-all
                ${step === s.id 
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30' 
                  : index < currentStepIndex
                    ? 'text-primary-400'
                    : 'text-surface-500'
                }
                ${index <= currentStepIndex ? 'cursor-pointer hover:bg-surface-800' : 'cursor-default'}
              `}
            >
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center
                ${step === s.id 
                  ? 'bg-primary-500 text-white' 
                  : index < currentStepIndex
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'bg-surface-800 text-surface-500'
                }
              `}>
                {index < currentStepIndex ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <s.icon className="w-4 h-4" />
                )}
              </div>
              <span className="font-medium">{s.label}</span>
            </button>
            {index < steps.length - 1 && (
              <ChevronRight className="w-5 h-5 text-surface-600 mx-2" />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="bg-surface-900/50 backdrop-blur-sm rounded-2xl border border-surface-800 p-8">
        <AnimatePresence mode="wait">
          {step === 'prd' && (
            <StepPRD
              key="prd"
              content={prdContent}
              title={prdTitle}
              parsedIntent={parsedIntent}
              isParsingIntent={parseIntent.isPending}
              parseError={parseIntent.error?.message}
              onContentChange={setPrdContent}
              onTitleChange={setPrdTitle}
              onParseIntent={() => parseIntent.mutate()}
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
  parsedIntent,
  isParsingIntent,
  parseError,
  onContentChange,
  onTitleChange,
  onParseIntent,
  onNext,
}: {
  content: string
  title: string
  parsedIntent: ParsedIntent | null
  isParsingIntent: boolean
  parseError?: string
  onContentChange: (v: string) => void
  onTitleChange: (v: string) => void
  onParseIntent: () => void
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
      <div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Product Requirement Document
        </h2>
        <p className="text-surface-400">
          Paste your PRD content or upload a markdown file
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-surface-300 mb-2">
          Title
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="e.g., User Authentication Feature"
          className="w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                     text-white placeholder-surface-500 focus:border-primary-500 focus:ring-1 
                     focus:ring-primary-500 transition-all"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-surface-300 mb-2">
          PRD Content (Markdown)
        </label>
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
          rows={15}
          className="w-full px-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                     text-white placeholder-surface-500 focus:border-primary-500 focus:ring-1 
                     focus:ring-primary-500 transition-all font-mono text-sm resize-none"
        />
      </div>

      {/* Intent Preview Button */}
      {content.trim() && (
        <div className="flex items-center gap-4">
          <button
            onClick={onParseIntent}
            disabled={isParsingIntent}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border border-amber-500/30 
                       text-amber-400 font-medium rounded-lg hover:bg-amber-500/20 
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
              className="flex items-center gap-2 text-sm text-surface-400 hover:text-white transition-colors"
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

      {/* Parse Error */}
      {parseError && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Analysis Failed</p>
            <p className="text-sm text-red-300">{parseError}</p>
          </div>
        </div>
      )}

      {/* Intent Preview */}
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

      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={!content.trim()}
          className="flex items-center gap-2 px-6 py-3 bg-primary-500 text-white font-medium 
                     rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
        >
          Continue
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  )
}

function IntentPreviewCard({ intent }: { intent: ParsedIntent }) {
  return (
    <div className="p-5 rounded-xl bg-amber-500/5 border border-amber-500/20 space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
          <Target className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h3 className="font-semibold text-white">{intent.title}</h3>
          <p className="text-sm text-surface-400">Intent Analysis Preview</p>
        </div>
      </div>

      {intent.summary && (
        <p className="text-sm text-surface-300 leading-relaxed">
          {intent.summary}
        </p>
      )}

      <div className="grid grid-cols-3 gap-4">
        <IntentStatBox 
          icon={Layers} 
          label="Features" 
          value={intent.features.length} 
          color="primary"
        />
        <IntentStatBox 
          icon={Code} 
          label="API Changes" 
          value={intent.api_changes.length} 
          color="cyan"
        />
        <IntentStatBox 
          icon={Database} 
          label="Data Entities" 
          value={intent.data_entities.length} 
          color="orange"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="flex items-center gap-2 text-surface-400">
          <Users className="w-4 h-4" />
          <span>{intent.user_stories.length} User Stories</span>
        </div>
        <div className="flex items-center gap-2 text-surface-400">
          <Lock className="w-4 h-4" />
          <span>{intent.auth_requirements.length} Auth Requirements</span>
        </div>
        <div className="flex items-center gap-2 text-surface-400">
          <Globe className="w-4 h-4" />
          <span>{intent.external_integrations.length} Integrations</span>
        </div>
        <div className="flex items-center gap-2 text-red-400">
          <Shield className="w-4 h-4" />
          <span>{intent.data_entities.filter(e => e.is_sensitive).length} Sensitive Data</span>
        </div>
      </div>
    </div>
  )
}

function IntentStatBox({ 
  icon: Icon, 
  label, 
  value, 
  color 
}: { 
  icon: typeof Layers
  label: string
  value: number
  color: string
}) {
  const colorClasses: Record<string, string> = {
    primary: 'bg-primary-500/20 text-primary-400 border-primary-500/30',
    cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  }

  return (
    <div className={`${colorClasses[color]} rounded-lg border p-3 text-center`}>
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
  onNext,
  onBack,
}: {
  path: string
  languages: string[]
  onPathChange: (v: string) => void
  onLanguagesChange: (v: string[]) => void
  onNext: () => void
  onBack: () => void
}) {
  const [browseError, setBrowseError] = useState<string | null>(null)
  const [isElectron] = useState(() => !!(window as any).electronAPI)
  
  const toggleLanguage = (lang: string) => {
    if (languages.includes(lang)) {
      onLanguagesChange(languages.filter(l => l !== lang))
    } else {
      onLanguagesChange([...languages, lang])
    }
  }

  // Handle directory selection - works in both Electron and modern browsers
  const handleBrowse = async () => {
    setBrowseError(null)
    
    // Check if running in Electron
    if ((window as any).electronAPI?.selectDirectory) {
      const selectedPath = await (window as any).electronAPI.selectDirectory()
      if (selectedPath) {
        onPathChange(selectedPath)
      }
      return
    }
    
    // Use File System Access API for modern browsers (Chrome, Edge)
    if ('showDirectoryPicker' in window) {
      try {
        const dirHandle = await (window as any).showDirectoryPicker({
          mode: 'read',
        })
        // Get the directory name - in browser we can't get the full path
        // but we can use the handle for further operations
        onPathChange(dirHandle.name)
        // Store the handle for potential future use
        ;(window as any).__selectedDirHandle = dirHandle
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setBrowseError('Failed to select directory')
        }
      }
      return
    }
    
    // Fallback for unsupported browsers
    setBrowseError('Directory browsing is not supported in this browser. Please enter the path manually or use Chrome/Edge.')
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Codebase Configuration
        </h2>
        <p className="text-surface-400">
          Specify the path to your codebase and select languages to analyze
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-surface-300 mb-2">
          Codebase Path
        </label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <FolderOpen className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
            <input
              type="text"
              value={path}
              onChange={(e) => onPathChange(e.target.value)}
              placeholder={isElectron ? "/path/to/your/codebase" : "Enter path or click Browse"}
              className="w-full pl-12 pr-4 py-3 bg-surface-800 border border-surface-700 rounded-lg
                         text-white placeholder-surface-500 focus:border-primary-500 focus:ring-1 
                         focus:ring-primary-500 transition-all"
            />
          </div>
          <button
            onClick={handleBrowse}
            className="flex items-center gap-2 px-4 py-3 bg-surface-800 border border-surface-700 
                       text-surface-300 font-medium rounded-lg hover:bg-surface-700 hover:border-surface-600
                       transition-all"
          >
            <FolderOpen className="w-4 h-4" />
            Browse
          </button>
        </div>
        {browseError && (
          <p className="text-sm text-red-400 mt-2">{browseError}</p>
        )}
        {!isElectron && (
          <p className="text-xs text-surface-500 mt-2">
            Tip: For full filesystem access, use the desktop app or enter a server-accessible path.
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-surface-300 mb-3">
          Languages to Analyze
        </label>
        <div className="flex flex-wrap gap-3">
          {['python', 'kotlin', 'typescript', 'javascript'].map(lang => (
            <button
              key={lang}
              onClick={() => toggleLanguage(lang)}
              className={`
                px-4 py-2 rounded-lg border font-medium capitalize transition-all
                ${languages.includes(lang)
                  ? 'bg-primary-500/20 border-primary-500/50 text-primary-400'
                  : 'bg-surface-800 border-surface-700 text-surface-400 hover:border-surface-600'
                }
              `}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="px-6 py-3 text-surface-400 hover:text-white transition-colors"
        >
          Back
        </button>
        <button
          onClick={onNext}
          disabled={!path.trim() || languages.length === 0}
          className="flex items-center gap-2 px-6 py-3 bg-primary-500 text-white font-medium 
                     rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
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
      // Don't allow deselecting all dimensions - at least one must be selected
      if (dimensions.length > 1) {
        onDimensionsChange(dimensions.filter(d => d !== dim))
      }
    } else {
      onDimensionsChange([...dimensions, dim])
    }
  }

  const dimensionInfo = {
    security: {
      icon: Shield,
      label: 'Security',
      description: 'STRIDE threat modeling, OWASP Top 10, attack surface analysis',
      color: 'primary',
    },
    privacy: {
      icon: Eye,
      label: 'Privacy',
      description: 'LINDDUN framework, GDPR/CCPA compliance, data protection',
      color: 'purple',
    },
    compliance: {
      icon: FileCheck,
      label: 'Compliance',
      description: 'SOC 2, HIPAA, PCI-DSS, ISO 27001 framework analysis',
      color: 'blue',
    },
    engineering: {
      icon: Code,
      label: 'Engineering',
      description: 'Code quality, maintainability, technical debt, best practices',
      color: 'green',
    },
    architecture: {
      icon: Layers,
      label: 'Architecture',
      description: 'System design, scalability, patterns, component coupling',
      color: 'orange',
    },
  }
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Analysis Configuration
        </h2>
        <p className="text-surface-400">
          Configure how the product review should be performed
        </p>
      </div>

      {/* Review Dimensions Selection */}
      <div>
        <label className="block text-sm font-medium text-surface-300 mb-3">
          Review Dimensions
        </label>
        <p className="text-sm text-surface-400 mb-4">
          Select which types of analysis to perform. You can run multiple dimensions together for a comprehensive cross-functional review.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(Object.keys(dimensionInfo) as Array<keyof typeof dimensionInfo>).map((dim) => {
            const info = dimensionInfo[dim]
            const Icon = info.icon
            const isSelected = dimensions.includes(dim)
            const colorClasses = {
              primary: isSelected ? 'bg-primary-500/20 border-primary-500/50 text-primary-400' : 'bg-surface-800 border-surface-700 text-surface-400',
              purple: isSelected ? 'bg-purple-500/20 border-purple-500/50 text-purple-400' : 'bg-surface-800 border-surface-700 text-surface-400',
              blue: isSelected ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' : 'bg-surface-800 border-surface-700 text-surface-400',
              green: isSelected ? 'bg-green-500/20 border-green-500/50 text-green-400' : 'bg-surface-800 border-surface-700 text-surface-400',
              orange: isSelected ? 'bg-orange-500/20 border-orange-500/50 text-orange-400' : 'bg-surface-800 border-surface-700 text-surface-400',
            }
            
            return (
              <button
                key={dim}
                onClick={() => toggleDimension(dim)}
                disabled={isSelected && dimensions.length === 1}
                className={`
                  p-4 rounded-lg border text-left transition-all
                  ${colorClasses[info.color as keyof typeof colorClasses]}
                  ${isSelected && dimensions.length === 1 ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-surface-600'}
                `}
              >
                <div className="flex items-start gap-3">
                  <div className={`
                    w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0
                    ${isSelected 
                      ? info.color === 'primary' ? 'bg-primary-500/20' 
                        : info.color === 'purple' ? 'bg-purple-500/20' 
                        : info.color === 'blue' ? 'bg-blue-500/20'
                        : info.color === 'green' ? 'bg-green-500/20'
                        : 'bg-orange-500/20'
                      : 'bg-surface-700'
                    }
                  `}>
                    <Icon className={`w-5 h-5 ${isSelected 
                      ? info.color === 'primary' ? 'text-primary-400' 
                        : info.color === 'purple' ? 'text-purple-400' 
                        : info.color === 'blue' ? 'text-blue-400'
                        : info.color === 'green' ? 'text-green-400'
                        : 'text-orange-400' 
                      : 'text-surface-500'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium">{info.label}</p>
                      {isSelected && (
                        <Check className="w-4 h-4" />
                      )}
                    </div>
                    <p className="text-xs opacity-80 leading-relaxed">
                      {info.description}
                    </p>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
        {dimensions.length >= 3 && (
          <div className="mt-3 p-3 rounded-lg bg-primary-500/10 border border-primary-500/30">
            <p className="text-sm text-primary-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Cross-functional review enabled: {dimensions.length} dimensions will be analyzed in parallel
            </p>
          </div>
        )}
      </div>

      {/* LLM Toggle */}
      <div className="space-y-4">
        <label className="flex items-center justify-between p-4 rounded-lg bg-surface-800 border border-surface-700 cursor-pointer hover:border-surface-600 transition-all">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <p className="font-medium text-white">LLM-Powered Analysis</p>
              <p className="text-sm text-surface-400">
                Use OpenAI + Anthropic for deeper semantic analysis
              </p>
            </div>
          </div>
          <div className="relative">
            <input
              type="checkbox"
              checked={useLLM}
              onChange={(e) => onUseLLMChange(e.target.checked)}
              className="sr-only"
            />
            <div className={`
              w-14 h-8 rounded-full transition-colors
              ${useLLM ? 'bg-primary-500' : 'bg-surface-700'}
            `}>
              <div className={`
                w-6 h-6 rounded-full bg-white shadow-lg transition-transform mt-1
                ${useLLM ? 'translate-x-7' : 'translate-x-1'}
              `} />
            </div>
          </div>
        </label>

        {/* API Keys Section - shown when LLM is enabled */}
        {useLLM && (
          <div className="p-4 rounded-lg bg-surface-800/50 border border-surface-700 space-y-4">
            <div className="flex items-center gap-3">
              <Key className="w-5 h-5 text-primary-400" />
              <div>
                <p className="font-medium text-white">API Keys</p>
                <p className="text-xs text-surface-400">
                  Required for AI-powered analysis. At least one key is needed.
                </p>
              </div>
            </div>

            {/* Warning if no API keys */}
            {!hasApiKeys && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-amber-400 font-medium">No API keys provided</p>
                  <p className="text-xs text-amber-300/80 mt-0.5">
                    Without API keys, the review will fall back to pattern-based analysis only.
                  </p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-surface-400 mb-1.5">
                  OpenAI API Key
                </label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => onOpenaiKeyChange(e.target.value)}
                  placeholder="sk-..."
                  className="w-full px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg
                             text-white placeholder-surface-500 text-sm
                             focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-surface-400 mb-1.5">
                  Anthropic API Key
                </label>
                <input
                  type="password"
                  value={anthropicKey}
                  onChange={(e) => onAnthropicKeyChange(e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg
                             text-white placeholder-surface-500 text-sm
                             focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                />
              </div>
            </div>

            <p className="text-xs text-surface-500">
              Keys are only used for this request and are not stored. 
              Alternatively, set <code className="text-primary-400">OPENAI_API_KEY</code> or{' '}
              <code className="text-primary-400">ANTHROPIC_API_KEY</code> environment variables on the server.
            </p>

            {hasApiKeys && (
              <div className="flex items-center gap-2 text-green-400 text-sm">
                <Check className="w-4 h-4" />
                <span>API key provided - AI analysis will be enabled</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-4 rounded-lg bg-surface-800/50 border border-surface-700">
        <h3 className="font-medium text-white mb-3">Analysis Features</h3>
        <ul className="space-y-2 text-sm">
          {dimensions.includes('security') && (
            <>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-primary-400" />
                Security: STRIDE Threat Modeling
              </li>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-primary-400" />
                Security: OWASP Top 10 Pattern Matching
              </li>
            </>
          )}
          {dimensions.includes('privacy') && (
            <>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-purple-400" />
                Privacy: LINDDUN Framework Analysis
              </li>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-purple-400" />
                Privacy: GDPR/CCPA Compliance Check
              </li>
            </>
          )}
          {dimensions.includes('compliance') && (
            <>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-blue-400" />
                Compliance: SOC 2, HIPAA, PCI-DSS Analysis
              </li>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-blue-400" />
                Compliance: ISO 27001 Framework Check
              </li>
            </>
          )}
          {dimensions.includes('engineering') && (
            <>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-green-400" />
                Engineering: Code Quality Analysis
              </li>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-green-400" />
                Engineering: Technical Debt Assessment
              </li>
            </>
          )}
          {dimensions.includes('architecture') && (
            <>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-orange-400" />
                Architecture: System Design Patterns
              </li>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-orange-400" />
                Architecture: Scalability Analysis
              </li>
            </>
          )}
          <li className="flex items-center gap-2 text-surface-300">
            <Check className="w-4 h-4 text-primary-400" />
            Intent Analysis
          </li>
          {useLLM && (
            <>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-accent-400" />
                Parallel OpenAI + Anthropic Analysis
              </li>
              <li className="flex items-center gap-2 text-surface-300">
                <Check className="w-4 h-4 text-accent-400" />
                Semantic Intent Understanding
              </li>
            </>
          )}
        </ul>
      </div>

      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="px-6 py-3 text-surface-400 hover:text-white transition-colors"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-3 bg-primary-500 text-white font-medium 
                     rounded-lg hover:bg-primary-600 transition-all"
        >
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
        <h2 className="text-xl font-semibold text-white mb-2">
          Review Summary
        </h2>
        <p className="text-surface-400">
          Confirm your configuration and start the product review
        </p>
      </div>

      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-surface-800 border border-surface-700">
          <div className="flex items-center gap-3 mb-2">
            <FileText className="w-5 h-5 text-primary-400" />
            <span className="font-medium text-white">PRD</span>
          </div>
          <p className="text-surface-400 text-sm">{prdTitle || 'Untitled'}</p>
          {parsedIntent && (
            <div className="mt-3 pt-3 border-t border-surface-700 flex items-center gap-4 text-xs text-surface-500">
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

        <div className="p-4 rounded-lg bg-surface-800 border border-surface-700">
          <div className="flex items-center gap-3 mb-2">
            <Code className="w-5 h-5 text-primary-400" />
            <span className="font-medium text-white">Codebase</span>
          </div>
          <p className="text-surface-400 text-sm font-mono">{codebasePath}</p>
        </div>

        <div className="p-4 rounded-lg bg-surface-800 border border-surface-700">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="w-5 h-5 text-primary-400" />
            <span className="font-medium text-white">Analysis</span>
          </div>
          <div className="space-y-2">
            {useLLM && hasApiKeys ? (
              <div className="flex items-center gap-2 text-green-400 text-sm">
                <Check className="w-4 h-4" />
                <span>AI-powered analysis (LLM only)</span>
              </div>
            ) : useLLM && !hasApiKeys ? (
              <div className="flex items-center gap-2 text-amber-400 text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>LLM enabled but no API keys - will use pattern-based</span>
              </div>
            ) : (
              <p className="text-surface-400 text-sm">Pattern-based analysis only</p>
            )}
            <div className="flex flex-wrap gap-2">
              {dimensions.map(dim => (
                <span
                  key={dim}
                  className="px-2 py-1 text-xs rounded bg-primary-500/20 text-primary-400 border border-primary-500/30"
                >
                  {dimensionLabels[dim] || dim}
                </span>
              ))}
            </div>
            {dimensions.length >= 3 && (
              <p className="text-xs text-primary-400 mt-2 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Cross-functional review enabled ({dimensions.length} dimensions)
              </p>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Error</p>
            <p className="text-sm text-red-300">{error}</p>
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button
          onClick={onBack}
          disabled={isLoading}
          className="px-6 py-3 text-surface-400 hover:text-white transition-colors disabled:opacity-50"
        >
          Back
        </button>
        <button
          onClick={onSubmit}
          disabled={isLoading}
          className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-primary-500 to-accent-500 
                     text-white font-medium rounded-lg hover:from-primary-600 hover:to-accent-600 
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all glow-primary"
        >
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
