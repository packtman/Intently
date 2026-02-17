import { useState, useEffect, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Network, ZoomIn, ZoomOut, Filter, AlertTriangle, Shield, Database, Globe, Code, Users } from 'lucide-react'

interface GraphNode {
  id: string
  name: string
  type: string
  sensitive: boolean
  requires_auth: boolean
  trust_level: number
  risk_score: number
  is_new: boolean
  source: string
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  crosses_boundary: boolean
  requires_encryption: boolean
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  analysis: {
    unauthenticated_paths: number
    trust_boundary_crossings: number
    high_risk_entity_ids: string[]
  }
  stats: {
    total_entities: number
    total_relationships: number
    entity_types: Record<string, number>
    new_entities: number
  }
}

interface ImpactGraphProps {
  reviewId: string
}

const NODE_COLORS: Record<string, string> = {
  pii: '#ef4444',
  secret: '#dc2626',
  api: '#3b82f6',
  endpoint: '#60a5fa',
  service: '#22c55e',
  database: '#a855f7',
  user: '#f97316',
  queue: '#06b6d4',
  function: '#6b7280',
  class: '#6b7280',
  module: '#6b7280',
  data: '#eab308',
  auth_provider: '#14b8a6',
  trust_boundary: '#f43f5e',
  security_control: '#10b981',
}

const TYPE_ICONS: Record<string, typeof Shield> = {
  pii: AlertTriangle,
  secret: Shield,
  api: Globe,
  endpoint: Globe,
  service: Code,
  database: Database,
  user: Users,
}

export default function ImpactGraph({ reviewId }: ImpactGraphProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animFrameRef = useRef<number>(0)
  const nodesRef = useRef<GraphNode[]>([])

  useEffect(() => {
    fetchGraph()
  }, [reviewId])

  const fetchGraph = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/reviews/${reviewId}/graph`)
      if (!res.ok) {
        if (res.status === 403) throw new Error('Enable FEATURE_IMPACT_GRAPH=true')
        throw new Error(`HTTP ${res.status}`)
      }
      const data: GraphData = await res.json()
      setGraphData(data)
      initializePositions(data.nodes)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const initializePositions = (nodes: GraphNode[]) => {
    const w = 700
    const h = 500
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length
      const r = Math.min(w, h) * 0.35
      node.x = w / 2 + r * Math.cos(angle) + (Math.random() - 0.5) * 40
      node.y = h / 2 + r * Math.sin(angle) + (Math.random() - 0.5) * 40
      node.vx = 0
      node.vy = 0
    })
    nodesRef.current = nodes
    runSimulation(nodes)
  }

  const runSimulation = useCallback((nodes: GraphNode[]) => {
    if (!canvasRef.current || !graphData) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const w = canvas.width
    const h = canvas.height
    const edges = graphData.edges

    let iteration = 0
    const maxIterations = 120

    const tick = () => {
      if (iteration >= maxIterations) return

      // Simple force simulation
      const k = 0.01
      const repulsion = 5000
      const damping = 0.85

      // Repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = (nodes[j].x || 0) - (nodes[i].x || 0)
          const dy = (nodes[j].y || 0) - (nodes[i].y || 0)
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
          const force = repulsion / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          nodes[i].vx = (nodes[i].vx || 0) - fx
          nodes[i].vy = (nodes[i].vy || 0) - fy
          nodes[j].vx = (nodes[j].vx || 0) + fx
          nodes[j].vy = (nodes[j].vy || 0) + fy
        }
      }

      // Attraction along edges
      const nodeMap = new Map(nodes.map(n => [n.id, n]))
      for (const edge of edges) {
        const source = nodeMap.get(edge.source)
        const target = nodeMap.get(edge.target)
        if (!source || !target) continue
        const dx = (target.x || 0) - (source.x || 0)
        const dy = (target.y || 0) - (source.y || 0)
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const force = (dist - 100) * k
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        source.vx = (source.vx || 0) + fx
        source.vy = (source.vy || 0) + fy
        target.vx = (target.vx || 0) - fx
        target.vy = (target.vy || 0) - fy
      }

      // Center gravity
      for (const node of nodes) {
        node.vx = (node.vx || 0) + ((w / 2 - (node.x || 0)) * 0.001)
        node.vy = (node.vy || 0) + ((h / 2 - (node.y || 0)) * 0.001)
        node.vx = (node.vx || 0) * damping
        node.vy = (node.vy || 0) * damping
        node.x = Math.max(20, Math.min(w - 20, (node.x || 0) + (node.vx || 0)))
        node.y = Math.max(20, Math.min(h - 20, (node.y || 0) + (node.vy || 0)))
      }

      // Draw
      ctx.clearRect(0, 0, w, h)

      // Draw edges
      for (const edge of edges) {
        const source = nodeMap.get(edge.source)
        const target = nodeMap.get(edge.target)
        if (!source || !target) continue

        ctx.beginPath()
        ctx.moveTo(source.x || 0, source.y || 0)
        ctx.lineTo(target.x || 0, target.y || 0)
        if (edge.crosses_boundary) {
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.5)'
          ctx.setLineDash([5, 5])
          ctx.lineWidth = 2
        } else {
          ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)'
          ctx.setLineDash([])
          ctx.lineWidth = 1
        }
        ctx.stroke()
        ctx.setLineDash([])
      }

      // Draw nodes
      for (const node of nodes) {
        if (filter !== 'all') {
          if (filter === 'sensitive' && !node.sensitive) continue
          if (filter === 'new' && !node.is_new) continue
          if (filter === 'high_risk' && node.risk_score <= 70) continue
        }

        const color = NODE_COLORS[node.type] || '#6b7280'
        const radius = node.sensitive ? 10 : node.is_new ? 9 : 7

        // Glow for new entities
        if (node.is_new) {
          ctx.beginPath()
          ctx.arc(node.x || 0, node.y || 0, radius + 4, 0, Math.PI * 2)
          ctx.fillStyle = `${color}33`
          ctx.fill()
        }

        // Node circle
        ctx.beginPath()
        ctx.arc(node.x || 0, node.y || 0, radius, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()
        ctx.strokeStyle = node.sensitive ? '#fbbf24' : 'rgba(255,255,255,0.2)'
        ctx.lineWidth = node.sensitive ? 2 : 1
        ctx.stroke()

        // Label
        ctx.fillStyle = 'rgba(255,255,255,0.8)'
        ctx.font = '10px Inter, sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText(node.name.slice(0, 16), node.x || 0, (node.y || 0) + radius + 12)
      }

      iteration++
      animFrameRef.current = requestAnimationFrame(tick)
    }

    tick()
  }, [graphData, filter])

  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [])

  // Re-render when filter changes
  useEffect(() => {
    if (nodesRef.current.length > 0 && graphData) {
      runSimulation(nodesRef.current)
    }
  }, [filter, runSimulation])

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const clicked = nodesRef.current.find(n => {
      const dx = (n.x || 0) - x
      const dy = (n.y || 0) - y
      return Math.sqrt(dx * dx + dy * dy) < 12
    })
    setSelectedNode(clicked || null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400">
        <div className="animate-spin w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <Network className="w-8 h-8 text-surface-600 mx-auto mb-2" />
        <p className="text-sm text-surface-400">{error}</p>
      </div>
    )
  }

  if (!graphData) return null

  const { stats, analysis } = graphData

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-4 text-xs text-surface-400">
          <span>{stats.total_entities} entities</span>
          <span>{stats.total_relationships} relationships</span>
          {stats.new_entities > 0 && (
            <span className="text-primary-400">{stats.new_entities} new</span>
          )}
          {analysis.trust_boundary_crossings > 0 && (
            <span className="text-red-400">{analysis.trust_boundary_crossings} boundary crossings</span>
          )}
        </div>

        {/* Filters */}
        <div className="ml-auto flex items-center gap-1">
          <Filter className="w-3.5 h-3.5 text-surface-500" />
          {['all', 'sensitive', 'new', 'high_risk'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-1 rounded text-xs transition-colors ${
                filter === f
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                  : 'text-surface-400 hover:text-white hover:bg-surface-800'
              }`}
            >
              {f === 'all' ? 'All' : f === 'high_risk' ? 'High Risk' : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <div className="relative bg-surface-900 border border-surface-700 rounded-xl overflow-hidden">
        <canvas
          ref={canvasRef}
          width={700}
          height={500}
          className="w-full cursor-crosshair"
          onClick={handleCanvasClick}
        />

        {/* Legend */}
        <div className="absolute bottom-3 left-3 bg-surface-800/90 backdrop-blur-sm rounded-lg p-2 border border-surface-700">
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {Object.entries(stats.entity_types).slice(0, 6).map(([type, count]) => (
              <div key={type} className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS[type] || '#6b7280' }} />
                <span className="text-[10px] text-surface-400">{type} ({count})</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Selected node detail */}
      {selectedNode && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-800 border border-surface-700 rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-white">{selectedNode.name}</h4>
            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-700 text-surface-300 capitalize">{selectedNode.type}</span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <span className="text-surface-500">Risk Score</span>
              <p className={`font-medium ${selectedNode.risk_score > 70 ? 'text-red-400' : selectedNode.risk_score > 40 ? 'text-yellow-400' : 'text-green-400'}`}>
                {selectedNode.risk_score}/100
              </p>
            </div>
            <div>
              <span className="text-surface-500">Sensitive</span>
              <p className={`font-medium ${selectedNode.sensitive ? 'text-red-400' : 'text-surface-300'}`}>
                {selectedNode.sensitive ? 'Yes' : 'No'}
              </p>
            </div>
            <div>
              <span className="text-surface-500">Auth Required</span>
              <p className="font-medium text-surface-300">{selectedNode.requires_auth ? 'Yes' : 'No'}</p>
            </div>
          </div>
          {selectedNode.source && (
            <p className="text-xs text-surface-500 mt-2 truncate">Source: {selectedNode.source}</p>
          )}
        </motion.div>
      )}
    </div>
  )
}
