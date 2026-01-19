import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Code,
  FolderOpen,
  Sparkles,
  Check,
  Loader2,
  AlertCircle,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Download,
  Copy,
  Edit3,
  RefreshCw,
  Database,
  Lock,
  Network,
  Layers,
  BookOpen,
  Cpu,
  Package,
  Trash2,
  Eye,
  Settings,
} from 'lucide-react'
import { api } from '../services/api'
import { useBackend } from '../hooks/useBackend'
import type {
  PRDGeneratorRequest,
  GeneratedPRD,
  PRDGeneratorStatus,
  GeneratedPRDSection,
  PRDGeneratorConfig,
} from '../types'

type Step = 'codebase' | 'config' | 'generating' | 'result'

export default function PRDGenerator() {
  const { isConnected } = useBackend()
  const [step, setStep] = useState<Step>('codebase')
  const [codebasePath, setCodebasePath] = useState('')
  const [languages, setLanguages] = useState<string[]>(['python', 'typescript', 'javascript'])
  const [focusAreas, setFocusAreas] = useState<string[]>(['features', 'api', 'architecture'])
  const [detailLevel, setDetailLevel] = useState<'overview' | 'detailed' | 'comprehensive'>('detailed')
  const [includeApiDocs, setIncludeApiDocs] = useState(true)
  const [includeDataModels, setIncludeDataModels] = useState(true)
  const [includeAuthFlow, setIncludeAuthFlow] = useState(true)
  const [includeArchitecture, setIncludeArchitecture] = useState(true)
  const [generationId, setGenerationId] = useState<string | null>(null)
  const [generatedPRD, setGeneratedPRD] = useState<GeneratedPRD | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [editingSection, setEditingSection] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  // Fetch feature config
  const { data: config } = useQuery<PRDGeneratorConfig>({
    queryKey: ['prd-generator-config'],
    queryFn: () => api.getPRDGeneratorConfig(),
    staleTime: 5 * 60 * 1000,
  })

  const isEnabled = config?.enabled ?? true // Default to enabled if config not loaded

  // Poll for generation status
  const { data: generationStatus } = useQuery<PRDGeneratorStatus>({
    queryKey: ['prd-generation-status', generationId],
    queryFn: () => api.getPRDGeneratorStatus(generationId!),
    enabled: !!generationId && step === 'generating',
    refetchInterval: (data) => {
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 1000 // Poll every second
    },
  })

  // Handle generation completion
  useEffect(() => {
    if (generationStatus?.status === 'completed' && generationId) {
      api.getGeneratedPRD(generationId).then((prd) => {
        setGeneratedPRD(prd)
        setStep('result')
      })
    }
  }, [generationStatus?.status, generationId])

  const startGeneration = useMutation({
    mutationFn: async () => {
      const request: PRDGeneratorRequest = {
        codebase_path: codebasePath,
        languages,
        focus_areas: focusAreas,
        include_api_docs: includeApiDocs,
        include_data_models: includeDataModels,
        include_auth_flow: includeAuthFlow,
        include_architecture: includeArchitecture,
        output_format: 'markdown',
        detail_level: detailLevel,
      }
      return api.generatePRD(request)
    },
    onSuccess: (data) => {
      setGenerationId(data.generation_id)
      setStep('generating')
    },
  })

  const exportPRD = useMutation({
    mutationFn: async (format: 'markdown' | 'json' | 'html') => {
      if (!generationId) throw new Error('No generation ID')
      return api.exportGeneratedPRD(generationId, format)
    },
    onSuccess: (data) => {
      // Create download
      const blob = new Blob([data.content], { type: data.content_type })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = data.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
  })

  const updateSection = useMutation({
    mutationFn: async ({ sectionId, content }: { sectionId: string; content: string }) => {
      if (!generationId) throw new Error('No generation ID')
      return api.updatePRDSection(generationId, sectionId, content)
    },
    onSuccess: (_, variables) => {
      // Update local state
      if (generatedPRD) {
        const updateSectionContent = (sections: GeneratedPRDSection[]): GeneratedPRDSection[] => {
          return sections.map((s) => {
            if (s.id === variables.sectionId) {
              return { ...s, content: variables.content }
            }
            if (s.subsections) {
              return { ...s, subsections: updateSectionContent(s.subsections) }
            }
            return s
          })
        }
        setGeneratedPRD({
          ...generatedPRD,
          sections: updateSectionContent(generatedPRD.sections),
        })
      }
      setEditingSection(null)
      setEditContent('')
    },
  })

  const regenerateSection = useMutation({
    mutationFn: async ({ sectionId, instructions }: { sectionId: string; instructions?: string }) => {
      if (!generationId) throw new Error('No generation ID')
      return api.regeneratePRDSection(generationId, sectionId, instructions)
    },
    onSuccess: (data) => {
      // Update local state with regenerated section
      if (generatedPRD) {
        const updateSectionContent = (sections: GeneratedPRDSection[]): GeneratedPRDSection[] => {
          return sections.map((s) => {
            if (s.id === data.section.id) {
              return { ...s, content: data.section.content }
            }
            if (s.subsections) {
              return { ...s, subsections: updateSectionContent(s.subsections) }
            }
            return s
          })
        }
        setGeneratedPRD({
          ...generatedPRD,
          sections: updateSectionContent(generatedPRD.sections),
        })
      }
    },
  })

  const selectCodebase = async () => {
    const path = await window.electronAPI?.selectDirectory()
    if (path) {
      setCodebasePath(path)
    }
  }

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId)
    } else {
      newExpanded.add(sectionId)
    }
    setExpandedSections(newExpanded)
  }

  const startEditSection = (section: GeneratedPRDSection) => {
    setEditingSection(section.id)
    setEditContent(section.content)
  }

  const copyToClipboard = async (content: string) => {
    await navigator.clipboard.writeText(content)
    window.electronAPI?.showNotification('Copied', 'Content copied to clipboard')
  }

  const steps = [
    { id: 'codebase' as Step, label: 'Codebase', icon: Code },
    { id: 'config' as Step, label: 'Options', icon: Settings },
    { id: 'generating' as Step, label: 'Generate', icon: Sparkles },
    { id: 'result' as Step, label: 'Result', icon: FileText },
  ]

  const currentStepIndex = steps.findIndex((s) => s.id === step)

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-16 h-16 text-ember-400 mb-4" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Backend Required</h2>
        <p className="text-void-400 mb-6">Start the backend server to generate PRDs.</p>
      </div>
    )
  }

  if (!isEnabled) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <FileText className="w-16 h-16 text-void-500 mb-4" />
        <h2 className="text-xl font-display font-semibold text-white mb-2">Feature Not Enabled</h2>
        <p className="text-void-400 mb-6">
          PRD Generator is not enabled. Set <code className="text-neon-400">FEATURE_PRD_GENERATOR=true</code> to enable.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">PRD Generator</h1>
        <p className="text-void-400 mt-2">
          Generate comprehensive Product Requirement Documents from your codebase
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between bg-void-900/30 rounded-2xl p-2">
        {steps.map((s, index) => (
          <div key={s.id} className="flex items-center flex-1">
            <button
              onClick={() => {
                if (index <= currentStepIndex && s.id !== 'generating') {
                  setStep(s.id)
                }
              }}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-xl transition-all flex-1
                ${step === s.id
                  ? 'bg-neon-500/10 text-neon-400 border border-neon-500/30'
                  : index < currentStepIndex
                    ? 'text-neon-400 hover:bg-void-800'
                    : 'text-void-500'
                }
                ${index <= currentStepIndex && s.id !== 'generating' ? 'cursor-pointer' : 'cursor-default'}
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
          {step === 'codebase' && (
            <StepCodebase
              key="codebase"
              path={codebasePath}
              languages={languages}
              onPathChange={setCodebasePath}
              onLanguagesChange={setLanguages}
              onSelectDirectory={selectCodebase}
              onNext={() => setStep('config')}
            />
          )}
          {step === 'config' && (
            <StepConfig
              key="config"
              focusAreas={focusAreas}
              detailLevel={detailLevel}
              includeApiDocs={includeApiDocs}
              includeDataModels={includeDataModels}
              includeAuthFlow={includeAuthFlow}
              includeArchitecture={includeArchitecture}
              onFocusAreasChange={setFocusAreas}
              onDetailLevelChange={setDetailLevel}
              onIncludeApiDocsChange={setIncludeApiDocs}
              onIncludeDataModelsChange={setIncludeDataModels}
              onIncludeAuthFlowChange={setIncludeAuthFlow}
              onIncludeArchitectureChange={setIncludeArchitecture}
              onNext={() => startGeneration.mutate()}
              onBack={() => setStep('codebase')}
              isLoading={startGeneration.isPending}
              error={startGeneration.error?.message}
            />
          )}
          {step === 'generating' && (
            <StepGenerating
              key="generating"
              status={generationStatus}
              error={generationStatus?.error_message}
            />
          )}
          {step === 'result' && generatedPRD && (
            <StepResult
              key="result"
              prd={generatedPRD}
              expandedSections={expandedSections}
              editingSection={editingSection}
              editContent={editContent}
              onToggleSection={toggleSection}
              onStartEdit={startEditSection}
              onEditContentChange={setEditContent}
              onSaveEdit={(sectionId) => updateSection.mutate({ sectionId, content: editContent })}
              onCancelEdit={() => {
                setEditingSection(null)
                setEditContent('')
              }}
              onRegenerateSection={(sectionId) => regenerateSection.mutate({ sectionId })}
              onExport={(format) => exportPRD.mutate(format)}
              onCopy={copyToClipboard}
              isUpdating={updateSection.isPending}
              isRegenerating={regenerateSection.isPending}
              isExporting={exportPRD.isPending}
              onStartNew={() => {
                setStep('codebase')
                setGenerationId(null)
                setGeneratedPRD(null)
              }}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// Step Components

function StepCodebase({
  path,
  languages,
  onPathChange,
  onLanguagesChange,
  onSelectDirectory,
  onNext,
}: {
  path: string
  languages: string[]
  onPathChange: (v: string) => void
  onLanguagesChange: (v: string[]) => void
  onSelectDirectory: () => void
  onNext: () => void
}) {
  const toggleLanguage = (lang: string) => {
    if (languages.includes(lang)) {
      onLanguagesChange(languages.filter((l) => l !== lang))
    } else {
      onLanguagesChange([...languages, lang])
    }
  }

  const availableLanguages = [
    { id: 'python', label: 'Python', color: 'text-yellow-400' },
    { id: 'typescript', label: 'TypeScript', color: 'text-blue-400' },
    { id: 'javascript', label: 'JavaScript', color: 'text-yellow-300' },
    { id: 'kotlin', label: 'Kotlin', color: 'text-aurora-400' },
    { id: 'java', label: 'Java', color: 'text-red-400' },
    { id: 'go', label: 'Go', color: 'text-cyan-400' },
    { id: 'rust', label: 'Rust', color: 'text-orange-400' },
    { id: 'ruby', label: 'Ruby', color: 'text-red-300' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2">Select Codebase</h2>
        <p className="text-void-400">Choose the codebase you want to generate a PRD from</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-void-300 mb-2">Codebase Path</label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <FolderOpen className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
            <input
              type="text"
              value={path}
              onChange={(e) => onPathChange(e.target.value)}
              placeholder="/path/to/your/codebase"
              className="input-field pl-12 font-mono text-sm"
            />
          </div>
          <button onClick={onSelectDirectory} className="btn-secondary flex items-center gap-2">
            <FolderOpen className="w-4 h-4" />
            Browse
          </button>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-void-300 mb-3">Languages to Analyze</label>
        <div className="grid grid-cols-4 gap-3">
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

      <div className="flex justify-end pt-4">
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
  focusAreas,
  detailLevel,
  includeApiDocs,
  includeDataModels,
  includeAuthFlow,
  includeArchitecture,
  onFocusAreasChange,
  onDetailLevelChange,
  onIncludeApiDocsChange,
  onIncludeDataModelsChange,
  onIncludeAuthFlowChange,
  onIncludeArchitectureChange,
  onNext,
  onBack,
  isLoading,
  error,
}: {
  focusAreas: string[]
  detailLevel: 'overview' | 'detailed' | 'comprehensive'
  includeApiDocs: boolean
  includeDataModels: boolean
  includeAuthFlow: boolean
  includeArchitecture: boolean
  onFocusAreasChange: (v: string[]) => void
  onDetailLevelChange: (v: 'overview' | 'detailed' | 'comprehensive') => void
  onIncludeApiDocsChange: (v: boolean) => void
  onIncludeDataModelsChange: (v: boolean) => void
  onIncludeAuthFlowChange: (v: boolean) => void
  onIncludeArchitectureChange: (v: boolean) => void
  onNext: () => void
  onBack: () => void
  isLoading: boolean
  error?: string
}) {
  const toggleFocusArea = (area: string) => {
    if (focusAreas.includes(area)) {
      if (focusAreas.length > 1) {
        onFocusAreasChange(focusAreas.filter((a) => a !== area))
      }
    } else {
      onFocusAreasChange([...focusAreas, area])
    }
  }

  const focusAreaOptions = [
    { id: 'features', label: 'Features', icon: Layers, description: 'Core product features' },
    { id: 'api', label: 'API Design', icon: Network, description: 'Endpoints & contracts' },
    { id: 'architecture', label: 'Architecture', icon: Cpu, description: 'System design' },
    { id: 'data', label: 'Data Models', icon: Database, description: 'Entities & schemas' },
    { id: 'security', label: 'Security', icon: Lock, description: 'Auth & permissions' },
    { id: 'dependencies', label: 'Dependencies', icon: Package, description: 'Libraries & tools' },
  ]

  const detailLevels = [
    { id: 'overview', label: 'Overview', description: 'High-level summary' },
    { id: 'detailed', label: 'Detailed', description: 'Standard PRD depth' },
    { id: 'comprehensive', label: 'Comprehensive', description: 'Maximum detail' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2">Generation Options</h2>
        <p className="text-void-400">Customize what should be included in the generated PRD</p>
      </div>

      {/* Focus Areas */}
      <div>
        <label className="block text-sm font-medium text-void-300 mb-3">Focus Areas</label>
        <div className="grid grid-cols-3 gap-3">
          {focusAreaOptions.map((area) => {
            const Icon = area.icon
            const isSelected = focusAreas.includes(area.id)
            return (
              <button
                key={area.id}
                onClick={() => toggleFocusArea(area.id)}
                disabled={isSelected && focusAreas.length === 1}
                className={`
                  p-4 rounded-xl border text-left transition-all
                  ${isSelected
                    ? 'bg-neon-500/10 border-neon-500/50 text-neon-400'
                    : 'bg-void-800/50 border-void-700 text-void-400 hover:border-void-600'
                  }
                  ${isSelected && focusAreas.length === 1 ? 'cursor-not-allowed opacity-60' : ''}
                `}
              >
                <div className="flex items-center gap-3 mb-1">
                  <Icon className="w-5 h-5" />
                  <span className="font-medium text-white">{area.label}</span>
                  {isSelected && <Check className="w-4 h-4 ml-auto" />}
                </div>
                <p className="text-xs opacity-80">{area.description}</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* Detail Level */}
      <div>
        <label className="block text-sm font-medium text-void-300 mb-3">Detail Level</label>
        <div className="flex gap-3">
          {detailLevels.map((level) => (
            <button
              key={level.id}
              onClick={() => onDetailLevelChange(level.id as typeof detailLevel)}
              className={`
                flex-1 p-4 rounded-xl border text-center transition-all
                ${detailLevel === level.id
                  ? 'bg-aurora-500/10 border-aurora-500/50 text-aurora-400'
                  : 'bg-void-800/50 border-void-700 text-void-400 hover:border-void-600'
                }
              `}
            >
              <p className="font-medium text-white mb-1">{level.label}</p>
              <p className="text-xs opacity-80">{level.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Include Options */}
      <div>
        <label className="block text-sm font-medium text-void-300 mb-3">Include Sections</label>
        <div className="grid grid-cols-2 gap-3">
          <ToggleOption
            label="API Documentation"
            description="Endpoint details & examples"
            icon={BookOpen}
            checked={includeApiDocs}
            onChange={onIncludeApiDocsChange}
          />
          <ToggleOption
            label="Data Models"
            description="Entity schemas & relationships"
            icon={Database}
            checked={includeDataModels}
            onChange={onIncludeDataModelsChange}
          />
          <ToggleOption
            label="Auth Flow"
            description="Authentication & authorization"
            icon={Lock}
            checked={includeAuthFlow}
            onChange={onIncludeAuthFlowChange}
          />
          <ToggleOption
            label="Architecture"
            description="System design & patterns"
            icon={Network}
            checked={includeArchitecture}
            onChange={onIncludeArchitectureChange}
          />
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
          className="text-void-400 hover:text-white transition-colors px-4 py-2"
        >
          Back
        </button>
        <button onClick={onNext} disabled={isLoading} className="btn-primary flex items-center gap-2">
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Starting...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate PRD
            </>
          )}
        </button>
      </div>
    </motion.div>
  )
}

function ToggleOption({
  label,
  description,
  icon: Icon,
  checked,
  onChange,
}: {
  label: string
  description: string
  icon: typeof Database
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label
      className={`
        flex items-center gap-4 p-4 rounded-xl border cursor-pointer transition-all
        ${checked
          ? 'bg-neon-500/5 border-neon-500/30'
          : 'bg-void-800/30 border-void-700 hover:border-void-600'
        }
      `}
    >
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${checked ? 'bg-neon-500/20' : 'bg-void-800'}`}>
        <Icon className={`w-5 h-5 ${checked ? 'text-neon-400' : 'text-void-500'}`} />
      </div>
      <div className="flex-1">
        <p className="font-medium text-white">{label}</p>
        <p className="text-xs text-void-400">{description}</p>
      </div>
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div
          className={`
            w-12 h-7 rounded-full transition-colors
            ${checked ? 'bg-neon-500' : 'bg-void-700'}
          `}
        >
          <div
            className={`
              w-5 h-5 rounded-full bg-white shadow-lg transition-transform mt-1
              ${checked ? 'translate-x-6' : 'translate-x-1'}
            `}
          />
        </div>
      </div>
    </label>
  )
}

function StepGenerating({
  status,
  error,
}: {
  status?: PRDGeneratorStatus
  error?: string
}) {
  const progress = status?.progress ?? 0
  const currentStep = status?.current_step ?? 'Initializing...'
  const stepsCompleted = status?.steps_completed ?? []

  const generationSteps = [
    { id: 'scan', label: 'Scanning codebase' },
    { id: 'parse', label: 'Parsing source files' },
    { id: 'extract', label: 'Extracting features' },
    { id: 'analyze', label: 'Analyzing architecture' },
    { id: 'generate', label: 'Generating PRD' },
    { id: 'format', label: 'Formatting output' },
  ]

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center py-12"
      >
        <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center mb-6">
          <AlertCircle className="w-10 h-10 text-red-400" />
        </div>
        <h2 className="text-xl font-display font-semibold text-white mb-2">Generation Failed</h2>
        <p className="text-void-400 text-center max-w-md mb-6">{error}</p>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center py-8"
    >
      {/* Animated Logo */}
      <div className="relative w-24 h-24 mb-8">
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-neon-500/20 to-aurora-500/20 animate-pulse" />
        <div className="absolute inset-2 rounded-full bg-void-900 flex items-center justify-center">
          <Sparkles className="w-10 h-10 text-neon-400 animate-pulse" />
        </div>
        <svg className="absolute inset-0 w-full h-full -rotate-90">
          <circle
            cx="48"
            cy="48"
            r="44"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            className="text-void-700"
          />
          <circle
            cx="48"
            cy="48"
            r="44"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            className="text-neon-400"
            strokeDasharray={276.46}
            strokeDashoffset={276.46 * (1 - progress / 100)}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
      </div>

      <h2 className="text-xl font-display font-semibold text-white mb-2">Generating PRD</h2>
      <p className="text-neon-400 mb-8">{currentStep}</p>

      {/* Progress Bar */}
      <div className="w-full max-w-md mb-8">
        <div className="flex justify-between text-sm text-void-400 mb-2">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-2 bg-void-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-neon-500 to-aurora-500"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="w-full max-w-md space-y-3">
        {generationSteps.map((step, index) => {
          const isCompleted = stepsCompleted.includes(step.id)
          const isCurrent = currentStep.toLowerCase().includes(step.id)
          return (
            <div
              key={step.id}
              className={`
                flex items-center gap-3 px-4 py-2 rounded-lg transition-all
                ${isCompleted ? 'text-neon-400' : isCurrent ? 'text-white bg-void-800/50' : 'text-void-500'}
              `}
            >
              {isCompleted ? (
                <Check className="w-5 h-5" />
              ) : isCurrent ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-void-600" />
              )}
              <span>{step.label}</span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

function StepResult({
  prd,
  expandedSections,
  editingSection,
  editContent,
  onToggleSection,
  onStartEdit,
  onEditContentChange,
  onSaveEdit,
  onCancelEdit,
  onRegenerateSection,
  onExport,
  onCopy,
  isUpdating,
  isRegenerating,
  isExporting,
  onStartNew,
}: {
  prd: GeneratedPRD
  expandedSections: Set<string>
  editingSection: string | null
  editContent: string
  onToggleSection: (id: string) => void
  onStartEdit: (section: GeneratedPRDSection) => void
  onEditContentChange: (content: string) => void
  onSaveEdit: (sectionId: string) => void
  onCancelEdit: () => void
  onRegenerateSection: (sectionId: string) => void
  onExport: (format: 'markdown' | 'json' | 'html') => void
  onCopy: (content: string) => void
  isUpdating: boolean
  isRegenerating: boolean
  isExporting: boolean
  onStartNew: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-display font-bold text-white mb-2">{prd.title}</h2>
          <p className="text-void-400">{prd.summary}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onStartNew}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            New
          </button>
          <div className="relative group">
            <button className="btn-primary flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
              <ChevronDown className="w-4 h-4" />
            </button>
            <div className="absolute right-0 top-full mt-2 w-48 bg-void-800 border border-void-700 rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => onExport('markdown')}
                disabled={isExporting}
                className="w-full px-4 py-3 text-left text-void-300 hover:bg-void-700 hover:text-white transition-colors flex items-center gap-2 rounded-t-xl"
              >
                <FileText className="w-4 h-4" />
                Markdown
              </button>
              <button
                onClick={() => onExport('html')}
                disabled={isExporting}
                className="w-full px-4 py-3 text-left text-void-300 hover:bg-void-700 hover:text-white transition-colors flex items-center gap-2"
              >
                <Code className="w-4 h-4" />
                HTML
              </button>
              <button
                onClick={() => onExport('json')}
                disabled={isExporting}
                className="w-full px-4 py-3 text-left text-void-300 hover:bg-void-700 hover:text-white transition-colors flex items-center gap-2 rounded-b-xl"
              >
                <Database className="w-4 h-4" />
                JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* File Saved Banner */}
      {prd.output_file_path && (
        <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-neon-500/10 border border-neon-500/30">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-neon-400" />
            <div>
              <p className="text-sm text-neon-400 font-medium">PRD saved to file</p>
              <p className="text-xs text-neon-300/70 font-mono truncate max-w-xl">{prd.output_file_path}</p>
            </div>
          </div>
          <button
            onClick={() => onCopy(prd.output_file_path || '')}
            className="text-neon-400 hover:text-white transition-colors p-2"
            title="Copy path"
          >
            <Copy className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-4 gap-4">
        <MetadataCard
          icon={Code}
          label="Files Analyzed"
          value={prd.metadata.files_analyzed.toLocaleString()}
          color="neon"
        />
        <MetadataCard
          icon={Layers}
          label="Lines of Code"
          value={prd.metadata.lines_of_code.toLocaleString()}
          color="aurora"
        />
        <MetadataCard
          icon={Network}
          label="API Endpoints"
          value={prd.api_documentation.length.toString()}
          color="ember"
        />
        <MetadataCard
          icon={Database}
          label="Data Models"
          value={prd.data_models.length.toString()}
          color="purple"
        />
      </div>

      {/* Sections */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Document Sections</h3>
        {prd.sections.map((section) => (
          <SectionCard
            key={section.id}
            section={section}
            isExpanded={expandedSections.has(section.id)}
            isEditing={editingSection === section.id}
            editContent={editContent}
            onToggle={() => onToggleSection(section.id)}
            onStartEdit={() => onStartEdit(section)}
            onEditChange={onEditContentChange}
            onSaveEdit={() => onSaveEdit(section.id)}
            onCancelEdit={onCancelEdit}
            onRegenerate={() => onRegenerateSection(section.id)}
            onCopy={() => onCopy(section.content)}
            isUpdating={isUpdating}
            isRegenerating={isRegenerating}
          />
        ))}
      </div>

      {/* Features Summary */}
      {prd.features.length > 0 && (
        <div className="p-6 rounded-xl bg-void-800/30 border border-void-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-neon-400" />
            Detected Features ({prd.features.length})
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {prd.features.map((feature, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-void-900/50 border border-void-700">
                <p className="font-medium text-white mb-1">{feature.name}</p>
                <p className="text-sm text-void-400">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tech Stack */}
      {prd.technical_stack.length > 0 && (
        <div className="p-6 rounded-xl bg-void-800/30 border border-void-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-aurora-400" />
            Technical Stack
          </h3>
          <div className="flex flex-wrap gap-2">
            {prd.technical_stack.map((tech, idx) => (
              <span
                key={idx}
                className="px-3 py-1 rounded-lg bg-aurora-500/10 text-aurora-400 border border-aurora-500/30 text-sm"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}

function MetadataCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Code
  label: string
  value: string
  color: 'neon' | 'aurora' | 'ember' | 'purple'
}) {
  const colorClasses = {
    neon: 'bg-neon-500/10 text-neon-400 border-neon-500/30',
    aurora: 'bg-aurora-500/10 text-aurora-400 border-aurora-500/30',
    ember: 'bg-ember-500/10 text-ember-400 border-ember-500/30',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  }

  return (
    <div className={`${colorClasses[color]} rounded-xl border p-4 text-center`}>
      <Icon className="w-6 h-6 mx-auto mb-2" />
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs opacity-80">{label}</p>
    </div>
  )
}

function SectionCard({
  section,
  isExpanded,
  isEditing,
  editContent,
  onToggle,
  onStartEdit,
  onEditChange,
  onSaveEdit,
  onCancelEdit,
  onRegenerate,
  onCopy,
  isUpdating,
  isRegenerating,
}: {
  section: GeneratedPRDSection
  isExpanded: boolean
  isEditing: boolean
  editContent: string
  onToggle: () => void
  onStartEdit: () => void
  onEditChange: (content: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  onRegenerate: () => void
  onCopy: () => void
  isUpdating: boolean
  isRegenerating: boolean
}) {
  return (
    <div className="rounded-xl border border-void-700 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 bg-void-800/50 hover:bg-void-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-void-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-void-400" />
          )}
          <span className="font-medium text-white">{section.title}</span>
          {section.confidence < 0.7 && (
            <span className="px-2 py-0.5 text-xs rounded bg-ember-500/20 text-ember-400">
              Low confidence
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {section.source_files && section.source_files.length > 0 && (
            <span className="text-xs text-void-500">
              {section.source_files.length} source file{section.source_files.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 border-t border-void-700">
              {isEditing ? (
                <div className="space-y-4">
                  <textarea
                    value={editContent}
                    onChange={(e) => onEditChange(e.target.value)}
                    rows={10}
                    className="input-field font-mono text-sm resize-none"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={onCancelEdit}
                      disabled={isUpdating}
                      className="px-4 py-2 text-void-400 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={onSaveEdit}
                      disabled={isUpdating}
                      className="btn-primary flex items-center gap-2"
                    >
                      {isUpdating ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="prose prose-invert max-w-none mb-4">
                    <pre className="whitespace-pre-wrap text-sm text-void-300 font-sans">
                      {section.content}
                    </pre>
                  </div>
                  <div className="flex items-center gap-2 pt-4 border-t border-void-700">
                    <button
                      onClick={onStartEdit}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-void-400 hover:text-white hover:bg-void-800 rounded-lg transition-colors"
                    >
                      <Edit3 className="w-4 h-4" />
                      Edit
                    </button>
                    <button
                      onClick={onRegenerate}
                      disabled={isRegenerating}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-void-400 hover:text-white hover:bg-void-800 rounded-lg transition-colors"
                    >
                      {isRegenerating ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Regenerate
                    </button>
                    <button
                      onClick={onCopy}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-void-400 hover:text-white hover:bg-void-800 rounded-lg transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                      Copy
                    </button>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
