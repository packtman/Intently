import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users,
  Cpu,
  Database,
  Globe,
  Shield,
  ArrowRight,
  Trash2,
  AlertTriangle,
  Sparkles,
  Download,
  Plus,
  ChevronRight,
  ChevronDown,
  X,
  Square,
} from 'lucide-react'
import type {
  CanvasNode,
  CanvasEdge,
  CanvasTrustBoundary,
  ThreatOverlay,
  CanvasNodeType,
} from '../../types'

interface ThreatCanvasProps {
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  boundaries: CanvasTrustBoundary[]
  threats: ThreatOverlay[]
  onNodesChange: (nodes: CanvasNode[]) => void
  onEdgesChange: (edges: CanvasEdge[]) => void
  onBoundariesChange: (boundaries: CanvasTrustBoundary[]) => void
  onThreatsChange: (threats: ThreatOverlay[]) => void
  onSuggestThreats: () => void
  onExport: () => void
  isSuggesting?: boolean
}

const NODE_ICONS: Record<CanvasNodeType, typeof Users> = {
  actor: Users,
  process: Cpu,
  data_store: Database,
  external: Globe,
}

const NODE_COLORS: Record<CanvasNodeType, string> = {
  actor: '#3b82f6',
  process: '#22c55e',
  data_store: '#a855f7',
  external: '#f97316',
}

const NODE_LABELS: Record<CanvasNodeType, string> = {
  actor: 'Actor',
  process: 'Process',
  data_store: 'Data Store',
  external: 'External',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
}

const TRUST_COLORS = ['#ef4444', '#f97316', '#3b82f6', '#22c55e']

type Tool = 'select' | 'actor' | 'process' | 'data_store' | 'external' | 'edge' | 'boundary'

let idCounter = 0
function nextId(prefix: string) {
  idCounter++
  return `${prefix}-${Date.now()}-${idCounter}`
}

export function ThreatCanvas({
  nodes,
  edges,
  boundaries,
  threats,
  onNodesChange,
  onEdgesChange,
  onBoundariesChange,
  onThreatsChange,
  onSuggestThreats,
  onExport,
  isSuggesting = false,
}: ThreatCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [activeTool, setActiveTool] = useState<Tool>('select')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [edgeStart, setEdgeStart] = useState<string | null>(null)
  const [boundaryDraw, setBoundaryDraw] = useState<{ startX: number; startY: number } | null>(null)
  const [boundaryPreview, setBoundaryPreview] = useState<{ x: number; y: number; w: number; h: number } | null>(null)
  const [showThreats, setShowThreats] = useState(true)
  const [editingLabel, setEditingLabel] = useState<string | null>(null)
  const [editLabelValue, setEditLabelValue] = useState('')

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || null
  const selectedEdge = edges.find(e => e.id === selectedEdgeId) || null

  const getCanvasPos = useCallback((e: React.MouseEvent) => {
    if (!canvasRef.current) return { x: 0, y: 0 }
    const rect = canvasRef.current.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }, [])

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target !== canvasRef.current) return
    const pos = getCanvasPos(e)

    if (activeTool === 'boundary') {
      setBoundaryDraw({ startX: pos.x, startY: pos.y })
      setBoundaryPreview({ x: pos.x, y: pos.y, w: 0, h: 0 })
      return
    }

    if (['actor', 'process', 'data_store', 'external'].includes(activeTool)) {
      const newNode: CanvasNode = {
        id: nextId(activeTool),
        type: activeTool as CanvasNodeType,
        label: NODE_LABELS[activeTool as CanvasNodeType],
        x: pos.x - 60,
        y: pos.y - 40,
        width: 120,
        height: 80,
        properties: {},
      }
      onNodesChange([...nodes, newNode])
      setSelectedNodeId(newNode.id)
      setSelectedEdgeId(null)
      setActiveTool('select')
      return
    }

    setSelectedNodeId(null)
    setSelectedEdgeId(null)
  }, [activeTool, getCanvasPos, nodes, onNodesChange])

  const handleCanvasMouseMove = useCallback((e: React.MouseEvent) => {
    if (draggingNodeId) {
      const pos = getCanvasPos(e)
      onNodesChange(
        nodes.map(n =>
          n.id === draggingNodeId
            ? { ...n, x: pos.x - dragOffset.x, y: pos.y - dragOffset.y }
            : n
        )
      )
      return
    }
    if (boundaryDraw && boundaryPreview) {
      const pos = getCanvasPos(e)
      const x = Math.min(boundaryDraw.startX, pos.x)
      const y = Math.min(boundaryDraw.startY, pos.y)
      const w = Math.abs(pos.x - boundaryDraw.startX)
      const h = Math.abs(pos.y - boundaryDraw.startY)
      setBoundaryPreview({ x, y, w, h })
    }
  }, [draggingNodeId, dragOffset, getCanvasPos, nodes, onNodesChange, boundaryDraw, boundaryPreview])

  const handleCanvasMouseUp = useCallback(() => {
    setDraggingNodeId(null)
    if (boundaryDraw && boundaryPreview && boundaryPreview.w > 40 && boundaryPreview.h > 40) {
      const newBoundary: CanvasTrustBoundary = {
        id: nextId('boundary'),
        label: 'Trust Boundary',
        x: boundaryPreview.x,
        y: boundaryPreview.y,
        width: boundaryPreview.w,
        height: boundaryPreview.h,
        trust_level: 2,
        color: TRUST_COLORS[2],
      }
      onBoundariesChange([...boundaries, newBoundary])
      setActiveTool('select')
    }
    setBoundaryDraw(null)
    setBoundaryPreview(null)
  }, [boundaryDraw, boundaryPreview, boundaries, onBoundariesChange])

  const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation()
    const node = nodes.find(n => n.id === nodeId)
    if (!node) return

    if (activeTool === 'edge') {
      if (!edgeStart) {
        setEdgeStart(nodeId)
      } else if (edgeStart !== nodeId) {
        const newEdge: CanvasEdge = {
          id: nextId('edge'),
          source_id: edgeStart,
          target_id: nodeId,
          label: '',
          data_classification: 'unclassified',
          protocol: '',
          bidirectional: false,
        }
        onEdgesChange([...edges, newEdge])
        setEdgeStart(null)
        setActiveTool('select')
      }
      return
    }

    const pos = getCanvasPos(e)
    setDraggingNodeId(nodeId)
    setDragOffset({ x: pos.x - node.x, y: pos.y - node.y })
    setSelectedNodeId(nodeId)
    setSelectedEdgeId(null)
  }, [activeTool, edgeStart, nodes, edges, onEdgesChange, getCanvasPos])

  const handleDeleteSelected = useCallback(() => {
    if (selectedNodeId) {
      onNodesChange(nodes.filter(n => n.id !== selectedNodeId))
      onEdgesChange(edges.filter(e => e.source_id !== selectedNodeId && e.target_id !== selectedNodeId))
      const updated = threats.filter(
        t => !t.affected_node_ids.includes(selectedNodeId)
      )
      onThreatsChange(updated)
      setSelectedNodeId(null)
    }
    if (selectedEdgeId) {
      onEdgesChange(edges.filter(e => e.id !== selectedEdgeId))
      setSelectedEdgeId(null)
    }
  }, [selectedNodeId, selectedEdgeId, nodes, edges, threats, onNodesChange, onEdgesChange, onThreatsChange])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (editingLabel) return
        handleDeleteSelected()
      }
      if (e.key === 'Escape') {
        setActiveTool('select')
        setEdgeStart(null)
        setSelectedNodeId(null)
        setSelectedEdgeId(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleDeleteSelected, editingLabel])

  const nodeCenter = (nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId)
    if (!node) return { x: 0, y: 0 }
    return { x: node.x + node.width / 2, y: node.y + node.height / 2 }
  }

  const threatsForNode = (nodeId: string) =>
    threats.filter(t => t.affected_node_ids.includes(nodeId))

  const threatsForEdge = (edgeId: string) =>
    threats.filter(t => t.affected_edge_ids.includes(edgeId))

  const updateNodeProperty = (nodeId: string, key: string, value: any) => {
    onNodesChange(
      nodes.map(n =>
        n.id === nodeId
          ? { ...n, properties: { ...n.properties, [key]: value } }
          : n
      )
    )
  }

  const startLabelEdit = (id: string, currentLabel: string) => {
    setEditingLabel(id)
    setEditLabelValue(currentLabel)
  }

  const commitLabelEdit = () => {
    if (!editingLabel) return
    const isNode = nodes.some(n => n.id === editingLabel)
    if (isNode) {
      onNodesChange(nodes.map(n => n.id === editingLabel ? { ...n, label: editLabelValue } : n))
    } else {
      onBoundariesChange(boundaries.map(b => b.id === editingLabel ? { ...b, label: editLabelValue } : b))
    }
    setEditingLabel(null)
  }

  return (
    <div className="flex h-full min-h-[600px] bg-surface-950 rounded-xl border border-surface-800 overflow-hidden">
      {/* Left Toolbox */}
      <div className="w-14 bg-surface-900 border-r border-surface-800 flex flex-col items-center py-3 gap-1">
        <ToolButton icon={ArrowRight} label="Select" active={activeTool === 'select'} onClick={() => { setActiveTool('select'); setEdgeStart(null) }} />
        <div className="w-8 border-t border-surface-700 my-1" />
        <ToolButton icon={Users} label="Actor" active={activeTool === 'actor'} onClick={() => setActiveTool('actor')} color={NODE_COLORS.actor} />
        <ToolButton icon={Cpu} label="Process" active={activeTool === 'process'} onClick={() => setActiveTool('process')} color={NODE_COLORS.process} />
        <ToolButton icon={Database} label="Data Store" active={activeTool === 'data_store'} onClick={() => setActiveTool('data_store')} color={NODE_COLORS.data_store} />
        <ToolButton icon={Globe} label="External" active={activeTool === 'external'} onClick={() => setActiveTool('external')} color={NODE_COLORS.external} />
        <div className="w-8 border-t border-surface-700 my-1" />
        <ToolButton icon={ArrowRight} label="Edge" active={activeTool === 'edge'} onClick={() => { setActiveTool('edge'); setEdgeStart(null) }} />
        <ToolButton icon={Square} label="Boundary" active={activeTool === 'boundary'} onClick={() => setActiveTool('boundary')} color="#ef4444" />
        <div className="w-8 border-t border-surface-700 my-1" />
        <ToolButton icon={Trash2} label="Delete" active={false} onClick={handleDeleteSelected} color="#ef4444" />
      </div>

      {/* Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-surface-900/50 border-b border-surface-800">
          <div className="flex items-center gap-2 text-xs text-surface-400">
            <span>{nodes.length} elements</span>
            <span className="text-surface-600">|</span>
            <span>{edges.length} flows</span>
            <span className="text-surface-600">|</span>
            <span>{boundaries.length} boundaries</span>
            {threats.length > 0 && (
              <>
                <span className="text-surface-600">|</span>
                <span className="text-red-400">{threats.length} threats</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {threats.length > 0 && (
              <button
                onClick={() => setShowThreats(!showThreats)}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                  showThreats
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : 'text-surface-400 hover:text-white'
                }`}
              >
                <AlertTriangle className="w-3 h-3" />
                Threats
              </button>
            )}
            <button
              onClick={onSuggestThreats}
              disabled={isSuggesting || nodes.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-500/20 border border-primary-500/30 
                         text-primary-400 text-xs font-medium hover:bg-primary-500/30 transition-colors
                         disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isSuggesting ? 'Analyzing...' : 'AI Suggest'}
            </button>
            <button
              onClick={onExport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-800 border border-surface-700 
                         text-surface-300 text-xs font-medium hover:text-white hover:border-surface-600 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div
          ref={canvasRef}
          className="flex-1 relative overflow-auto"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(100,116,139,0.15) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            cursor: activeTool === 'select' ? 'default' : activeTool === 'edge' ? 'crosshair' : 'crosshair',
          }}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
        >
          {/* SVG layer for edges */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: 1200, minHeight: 800 }}>
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="rgba(148,163,184,0.6)" />
              </marker>
              <marker id="arrowhead-red" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="rgba(239,68,68,0.6)" />
              </marker>
            </defs>
            {edges.map(edge => {
              const src = nodeCenter(edge.source_id)
              const tgt = nodeCenter(edge.target_id)
              const hasThreats = showThreats && threatsForEdge(edge.id).length > 0
              const isSelected = edge.id === selectedEdgeId
              return (
                <g key={edge.id}>
                  <line
                    x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                    stroke={hasThreats ? 'rgba(239,68,68,0.5)' : isSelected ? 'rgba(56,189,248,0.8)' : 'rgba(148,163,184,0.4)'}
                    strokeWidth={isSelected ? 3 : hasThreats ? 2 : 1.5}
                    strokeDasharray={hasThreats ? '6 3' : 'none'}
                    markerEnd={hasThreats ? 'url(#arrowhead-red)' : 'url(#arrowhead)'}
                    style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
                    onClick={(e) => { e.stopPropagation(); setSelectedEdgeId(edge.id); setSelectedNodeId(null) }}
                  />
                  {edge.label && (
                    <text
                      x={(src.x + tgt.x) / 2}
                      y={(src.y + tgt.y) / 2 - 8}
                      textAnchor="middle"
                      fill="rgba(148,163,184,0.7)"
                      fontSize={10}
                    >
                      {edge.label}
                    </text>
                  )}
                </g>
              )
            })}
          </svg>

          {/* Trust boundaries */}
          {boundaries.map(b => (
            <div
              key={b.id}
              className="absolute rounded-xl border-2 border-dashed"
              style={{
                left: b.x,
                top: b.y,
                width: b.width,
                height: b.height,
                borderColor: b.color + '60',
                backgroundColor: b.color + '08',
              }}
            >
              <div
                className="absolute -top-3 left-3 px-2 py-0.5 rounded text-[10px] font-medium"
                style={{ backgroundColor: b.color + '20', color: b.color }}
              >
                {editingLabel === b.id ? (
                  <input
                    autoFocus
                    value={editLabelValue}
                    onChange={e => setEditLabelValue(e.target.value)}
                    onBlur={commitLabelEdit}
                    onKeyDown={e => e.key === 'Enter' && commitLabelEdit()}
                    className="bg-transparent outline-none w-24 text-[10px]"
                  />
                ) : (
                  <span onDoubleClick={() => startLabelEdit(b.id, b.label)}>
                    {b.label} (L{b.trust_level})
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Boundary draw preview */}
          {boundaryPreview && (
            <div
              className="absolute rounded-xl border-2 border-dashed border-red-500/40 bg-red-500/5"
              style={{
                left: boundaryPreview.x,
                top: boundaryPreview.y,
                width: boundaryPreview.w,
                height: boundaryPreview.h,
              }}
            />
          )}

          {/* Nodes */}
          {nodes.map(node => {
            const Icon = NODE_ICONS[node.type] || Cpu
            const color = NODE_COLORS[node.type] || '#6b7280'
            const isSelected = node.id === selectedNodeId
            const nodeThreats = showThreats ? threatsForNode(node.id) : []
            const isEdgeSource = edgeStart === node.id

            return (
              <div
                key={node.id}
                className={`absolute rounded-xl border-2 cursor-pointer transition-shadow select-none
                  ${isSelected ? 'ring-2 ring-primary-400 shadow-lg shadow-primary-500/20' : ''}
                  ${isEdgeSource ? 'ring-2 ring-yellow-400' : ''}
                `}
                style={{
                  left: node.x,
                  top: node.y,
                  width: node.width,
                  height: node.height,
                  borderColor: nodeThreats.length > 0 ? '#ef4444' : color + '60',
                  backgroundColor: '#0f172a',
                }}
                onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
              >
                <div className="flex flex-col items-center justify-center h-full gap-1 px-2">
                  <Icon className="w-5 h-5" style={{ color }} />
                  {editingLabel === node.id ? (
                    <input
                      autoFocus
                      value={editLabelValue}
                      onChange={e => setEditLabelValue(e.target.value)}
                      onBlur={commitLabelEdit}
                      onKeyDown={e => e.key === 'Enter' && commitLabelEdit()}
                      className="bg-transparent outline-none text-center text-[11px] text-white w-full"
                    />
                  ) : (
                    <span
                      className="text-[11px] text-surface-300 text-center truncate w-full"
                      onDoubleClick={() => startLabelEdit(node.id, node.label)}
                    >
                      {node.label}
                    </span>
                  )}
                </div>

                {/* Threat badge */}
                {nodeThreats.length > 0 && (
                  <div
                    className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center"
                    title={`${nodeThreats.length} threat(s)`}
                  >
                    <span className="text-[9px] text-white font-bold">{nodeThreats.length}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Right Panel: Properties + Threats */}
      <div className="w-72 bg-surface-900 border-l border-surface-800 flex flex-col overflow-y-auto">
        {/* Properties panel */}
        {selectedNode && (
          <div className="p-4 border-b border-surface-800">
            <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-3">
              Properties
            </h4>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-surface-500">Label</label>
                <input
                  value={selectedNode.label}
                  onChange={e => onNodesChange(nodes.map(n => n.id === selectedNode.id ? { ...n, label: e.target.value } : n))}
                  className="w-full mt-1 px-2 py-1 rounded bg-surface-800 border border-surface-700 text-white text-xs outline-none focus:border-primary-500"
                />
              </div>
              <div>
                <label className="text-[10px] text-surface-500">Type</label>
                <p className="text-xs text-white capitalize mt-1">{selectedNode.type.replace('_', ' ')}</p>
              </div>
              {selectedNode.type === 'process' && (
                <>
                  <label className="flex items-center gap-2 text-xs text-surface-300">
                    <input
                      type="checkbox"
                      checked={!!selectedNode.properties.requires_auth}
                      onChange={e => updateNodeProperty(selectedNode.id, 'requires_auth', e.target.checked)}
                      className="rounded border-surface-600"
                    />
                    Requires Auth
                  </label>
                  <label className="flex items-center gap-2 text-xs text-surface-300">
                    <input
                      type="checkbox"
                      checked={!!selectedNode.properties.rate_limiting}
                      onChange={e => updateNodeProperty(selectedNode.id, 'rate_limiting', e.target.checked)}
                      className="rounded border-surface-600"
                    />
                    Rate Limiting
                  </label>
                  <label className="flex items-center gap-2 text-xs text-surface-300">
                    <input
                      type="checkbox"
                      checked={!!selectedNode.properties.validates_input}
                      onChange={e => updateNodeProperty(selectedNode.id, 'validates_input', e.target.checked)}
                      className="rounded border-surface-600"
                    />
                    Validates Input
                  </label>
                </>
              )}
              {selectedNode.type === 'data_store' && (
                <>
                  <label className="flex items-center gap-2 text-xs text-surface-300">
                    <input
                      type="checkbox"
                      checked={!!selectedNode.properties.handles_pii}
                      onChange={e => updateNodeProperty(selectedNode.id, 'handles_pii', e.target.checked)}
                      className="rounded border-surface-600"
                    />
                    Handles PII
                  </label>
                  <label className="flex items-center gap-2 text-xs text-surface-300">
                    <input
                      type="checkbox"
                      checked={!!selectedNode.properties.encryption_at_rest}
                      onChange={e => updateNodeProperty(selectedNode.id, 'encryption_at_rest', e.target.checked)}
                      className="rounded border-surface-600"
                    />
                    Encryption at Rest
                  </label>
                  <label className="flex items-center gap-2 text-xs text-surface-300">
                    <input
                      type="checkbox"
                      checked={!!selectedNode.properties.audit_logging}
                      onChange={e => updateNodeProperty(selectedNode.id, 'audit_logging', e.target.checked)}
                      className="rounded border-surface-600"
                    />
                    Audit Logging
                  </label>
                </>
              )}
            </div>
          </div>
        )}

        {selectedEdge && (
          <div className="p-4 border-b border-surface-800">
            <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-3">
              Data Flow
            </h4>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-surface-500">Label</label>
                <input
                  value={selectedEdge.label}
                  onChange={e => onEdgesChange(edges.map(ed => ed.id === selectedEdge.id ? { ...ed, label: e.target.value } : ed))}
                  className="w-full mt-1 px-2 py-1 rounded bg-surface-800 border border-surface-700 text-white text-xs outline-none focus:border-primary-500"
                />
              </div>
              <div>
                <label className="text-[10px] text-surface-500">Classification</label>
                <select
                  value={selectedEdge.data_classification}
                  onChange={e => onEdgesChange(edges.map(ed => ed.id === selectedEdge.id ? { ...ed, data_classification: e.target.value } : ed))}
                  className="w-full mt-1 px-2 py-1 rounded bg-surface-800 border border-surface-700 text-white text-xs outline-none"
                >
                  <option value="unclassified">Unclassified</option>
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="pii">PII</option>
                  <option value="credentials">Credentials</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] text-surface-500">Protocol</label>
                <select
                  value={selectedEdge.protocol}
                  onChange={e => onEdgesChange(edges.map(ed => ed.id === selectedEdge.id ? { ...ed, protocol: e.target.value } : ed))}
                  className="w-full mt-1 px-2 py-1 rounded bg-surface-800 border border-surface-700 text-white text-xs outline-none"
                >
                  <option value="">Not specified</option>
                  <option value="HTTPS">HTTPS</option>
                  <option value="HTTP">HTTP</option>
                  <option value="gRPC">gRPC</option>
                  <option value="SQL">SQL</option>
                  <option value="message_queue">Message Queue</option>
                  <option value="TCP">TCP</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Threats List */}
        <div className="flex-1 p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider">
              Threats ({threats.length})
            </h4>
          </div>
          {threats.length === 0 ? (
            <div className="text-center py-8">
              <Shield className="w-8 h-8 text-surface-600 mx-auto mb-2" />
              <p className="text-xs text-surface-500">No threats identified yet.</p>
              <p className="text-[10px] text-surface-600 mt-1">Click "AI Suggest" to analyze.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {threats.map(threat => (
                <ThreatCard key={threat.id} threat={threat} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ToolButton({
  icon: Icon,
  label,
  active,
  onClick,
  color,
}: {
  icon: typeof Users
  label: string
  active: boolean
  onClick: () => void
  color?: string
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors
        ${active
          ? 'bg-primary-500/20 border border-primary-500/40 text-primary-400'
          : 'text-surface-400 hover:text-white hover:bg-surface-800'
        }
      `}
    >
      <Icon className="w-4 h-4" style={color && !active ? { color } : undefined} />
    </button>
  )
}

function ThreatCard({ threat }: { threat: ThreatOverlay }) {
  const [expanded, setExpanded] = useState(false)
  const color = SEVERITY_COLORS[threat.severity] || '#6b7280'

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{ borderColor: color + '40', backgroundColor: color + '08' }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-2 p-2 text-left"
      >
        <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" style={{ color }} />
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-white font-medium truncate">{threat.title}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[9px] font-medium uppercase" style={{ color }}>
              {threat.severity}
            </span>
            <span className="text-[9px] text-surface-500 capitalize">
              {threat.category.replace('_', ' ')}
            </span>
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-surface-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-surface-500 flex-shrink-0" />
        )}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-2 pb-2 space-y-2">
              <p className="text-[10px] text-surface-300 leading-relaxed">{threat.description}</p>
              {threat.mitigation && (
                <div className="p-1.5 rounded bg-green-500/10 border border-green-500/20">
                  <p className="text-[10px] text-green-300">{threat.mitigation}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
