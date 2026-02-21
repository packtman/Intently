import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Shield,
  Plus,
  Trash2,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import { ThreatCanvas as ThreatCanvasComponent } from '../components/security/ThreatCanvas'
import { api } from '../services/api'
import type {
  CanvasNode,
  CanvasEdge,
  CanvasTrustBoundary,
  ThreatOverlay,
  CanvasState,
  CanvasSummary,
} from '../types'

export default function ThreatCanvasPage() {
  const [searchParams] = useSearchParams()
  const reviewId = searchParams.get('review')
  const queryClient = useQueryClient()

  const [activeCanvasId, setActiveCanvasId] = useState<string | null>(null)
  const [nodes, setNodes] = useState<CanvasNode[]>([])
  const [edges, setEdges] = useState<CanvasEdge[]>([])
  const [boundaries, setBoundaries] = useState<CanvasTrustBoundary[]>([])
  const [threats, setThreats] = useState<ThreatOverlay[]>([])
  const [title, setTitle] = useState('Untitled Threat Model')
  const [isSuggesting, setIsSuggesting] = useState(false)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: canvases, isLoading: listLoading } = useQuery<CanvasSummary[]>({
    queryKey: ['threat-canvases'],
    queryFn: () => api.listThreatCanvases(),
    retry: false,
  })

  const loadCanvas = useCallback(async (canvasId: string) => {
    try {
      const canvas = await api.getThreatCanvas(canvasId)
      setActiveCanvasId(canvas.canvas_id)
      setNodes(canvas.nodes || [])
      setEdges(canvas.edges || [])
      setBoundaries(canvas.boundaries || [])
      setThreats(canvas.threats || [])
      setTitle(canvas.title || 'Untitled Threat Model')
    } catch {
      // Canvas may have been deleted
    }
  }, [])

  const createCanvas = useCallback(async () => {
    const canvas = await api.createThreatCanvas({
      title: 'New Threat Model',
      review_id: reviewId || undefined,
    })
    queryClient.invalidateQueries({ queryKey: ['threat-canvases'] })
    await loadCanvas(canvas.canvas_id)
  }, [reviewId, queryClient, loadCanvas])

  // Auto-load first canvas or create one
  useEffect(() => {
    if (activeCanvasId) return
    if (listLoading) return
    if (canvases && canvases.length > 0) {
      loadCanvas(canvases[0].canvas_id)
    }
  }, [canvases, listLoading, activeCanvasId, loadCanvas])

  // Auto-save with debounce
  const autoSave = useCallback(() => {
    if (!activeCanvasId) return
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(async () => {
      try {
        await api.updateThreatCanvas(activeCanvasId, {
          title,
          nodes,
          edges,
          boundaries,
          threats,
        })
      } catch {
        // Silently fail for auto-save
      }
    }, 1500)
  }, [activeCanvasId, title, nodes, edges, boundaries, threats])

  useEffect(() => {
    autoSave()
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [nodes, edges, boundaries, threats, title, autoSave])

  const handleSuggestThreats = useCallback(async () => {
    if (!activeCanvasId) return
    setIsSuggesting(true)
    try {
      // Save current state first
      await api.updateThreatCanvas(activeCanvasId, {
        title,
        nodes,
        edges,
        boundaries,
        threats,
      })
      const result = await api.suggestThreats(activeCanvasId)
      setThreats(result.threats)
    } catch (err) {
      console.error('Failed to suggest threats:', err)
    } finally {
      setIsSuggesting(false)
    }
  }, [activeCanvasId, title, nodes, edges, boundaries, threats])

  const handleExport = useCallback(async () => {
    if (!activeCanvasId) return
    try {
      // Save first
      await api.updateThreatCanvas(activeCanvasId, {
        title,
        nodes,
        edges,
        boundaries,
        threats,
      })
      const markdown = await api.exportThreatCanvas(activeCanvasId, 'markdown')
      const blob = new Blob([markdown], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${title.replace(/\s+/g, '_')}_threat_model.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }, [activeCanvasId, title, nodes, edges, boundaries, threats])

  const handleDelete = useCallback(async (canvasId: string) => {
    try {
      await api.deleteThreatCanvas(canvasId)
      queryClient.invalidateQueries({ queryKey: ['threat-canvases'] })
      if (activeCanvasId === canvasId) {
        setActiveCanvasId(null)
        setNodes([])
        setEdges([])
        setBoundaries([])
        setThreats([])
      }
    } catch {
      // ignore
    }
  }, [activeCanvasId, queryClient])

  const handlePopulateFromReview = useCallback(async () => {
    if (!activeCanvasId || !reviewId) return
    try {
      const result = await api.populateCanvasFromReview(activeCanvasId, reviewId)
      setNodes(result.nodes || [])
      setEdges(result.edges || [])
      setBoundaries(result.boundaries || [])
    } catch (err) {
      console.error('Failed to populate from review:', err)
    }
  }, [activeCanvasId, reviewId])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white flex items-center gap-3">
            <Shield className="w-8 h-8 text-primary-400" />
            Threat Model Canvas
          </h1>
          <p className="text-surface-400 mt-1">
            Visually map data flows, trust boundaries, and actors. AI suggests threats on the topology.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {reviewId && activeCanvasId && (
            <button
              onClick={handlePopulateFromReview}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500/20 border border-primary-500/30 
                         rounded-lg text-primary-400 hover:bg-primary-500/30 transition-all text-sm"
            >
              Populate from Review
            </button>
          )}
          <button
            onClick={createCanvas}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 rounded-lg text-white 
                       hover:bg-primary-600 transition-all text-sm"
          >
            <Plus className="w-4 h-4" />
            New Canvas
          </button>
        </div>
      </div>

      {/* Canvas Tabs */}
      {canvases && canvases.length > 1 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {canvases.map(c => (
            <button
              key={c.canvas_id}
              onClick={() => loadCanvas(c.canvas_id)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm whitespace-nowrap transition-colors
                ${activeCanvasId === c.canvas_id
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                  : 'bg-surface-800 text-surface-400 border border-surface-700 hover:text-white'
                }
              `}
            >
              <Shield className="w-3.5 h-3.5" />
              {c.title}
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(c.canvas_id) }}
                className="ml-1 text-surface-500 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </button>
          ))}
        </div>
      )}

      {/* Title editing */}
      {activeCanvasId && (
        <div>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="bg-transparent text-xl font-semibold text-white outline-none border-b border-transparent 
                       hover:border-surface-700 focus:border-primary-500 transition-colors pb-1 w-full max-w-md"
            placeholder="Threat model title..."
          />
        </div>
      )}

      {/* Main Canvas */}
      {activeCanvasId ? (
        <div style={{ height: 'calc(100vh - 280px)', minHeight: 500 }}>
          <ThreatCanvasComponent
            nodes={nodes}
            edges={edges}
            boundaries={boundaries}
            threats={threats}
            onNodesChange={setNodes}
            onEdgesChange={setEdges}
            onBoundariesChange={setBoundaries}
            onThreatsChange={setThreats}
            onSuggestThreats={handleSuggestThreats}
            onExport={handleExport}
            isSuggesting={isSuggesting}
          />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-24">
          {listLoading ? (
            <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
          ) : (
            <>
              <Shield className="w-16 h-16 text-surface-600 mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">No Threat Canvases</h2>
              <p className="text-surface-400 text-sm mb-6">Create a new canvas to start modeling threats.</p>
              <button
                onClick={createCanvas}
                className="flex items-center gap-2 px-6 py-3 bg-primary-500 rounded-lg text-white 
                           hover:bg-primary-600 transition-all"
              >
                <Plus className="w-5 h-5" />
                Create Threat Canvas
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
