import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, ChevronRight, Sparkles } from 'lucide-react'

interface Template {
  id: string
  name: string
  description: string
  category: string
  sections: Array<{ title: string; required: boolean; guidance: string }>
  keywords: string[]
}

interface TemplatePickerProps {
  onSelect: (markdown: string) => void
}

const CATEGORY_COLORS: Record<string, string> = {
  feature: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  api: 'text-green-400 bg-green-500/10 border-green-500/20',
  migration: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  integration: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
}

export default function TemplatePicker({ onSelect }: TemplatePickerProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (expanded && templates.length === 0) {
      fetchTemplates()
    }
  }, [expanded])

  const fetchTemplates = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/templates')
      if (res.ok) setTemplates(await res.json())
    } catch {}
    setLoading(false)
  }

  const selectTemplate = async (templateId: string) => {
    try {
      const res = await fetch(`/api/templates/${templateId}/render`)
      if (res.ok) {
        const data = await res.json()
        onSelect(data.markdown)
        setExpanded(false)
      }
    } catch {}
  }

  return (
    <div className="mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-primary-400 hover:text-primary-300 transition-colors"
      >
        <Sparkles className="w-3.5 h-3.5" />
        <span>Start from a template</span>
        <ChevronRight className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`} />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 overflow-hidden"
          >
            {loading ? (
              <div className="flex justify-center py-4">
                <div className="animate-spin w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full" />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {templates.map(template => (
                  <button
                    key={template.id}
                    onClick={() => selectTemplate(template.id)}
                    className="text-left p-3 rounded-lg bg-surface-800 border border-surface-700 hover:border-primary-500/40 transition-colors group"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-3.5 h-3.5 text-surface-400 group-hover:text-primary-400 transition-colors" />
                      <span className="text-xs font-medium text-white">{template.name}</span>
                      <span className={`text-[9px] px-1 py-0.5 rounded border ${CATEGORY_COLORS[template.category] || ''}`}>
                        {template.category}
                      </span>
                    </div>
                    <p className="text-[10px] text-surface-500 line-clamp-2">{template.description}</p>
                    <p className="text-[10px] text-surface-600 mt-1">
                      {template.sections.filter(s => s.required).length} required sections
                    </p>
                  </button>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
