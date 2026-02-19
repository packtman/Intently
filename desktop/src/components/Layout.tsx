import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  FileSearch,
  Settings,
  Zap,
  Circle,
  ChevronLeft,
  ChevronRight,
  Shield,
  Layers,
  Sparkles,
  BarChart3,
  MessageSquare,
} from 'lucide-react'
import { useBackend } from '../hooks/useBackend'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { isConnected, isLoading } = useBackend()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/new', label: 'New Review', icon: FileSearch },
    { path: '/bulk', label: 'Bulk Analysis', icon: Layers },
    { path: '/generate', label: 'PRD Generator', icon: Sparkles },
    { path: '/chat', label: 'Codebase Chat', icon: MessageSquare },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/settings', label: 'Settings', icon: Settings },
  ]

  return (
    <div className="h-screen flex bg-void-950 overflow-hidden">
      {/* Background Pattern */}
      <div className="fixed inset-0 pattern-grid opacity-50 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-radial from-neon-500/5 via-transparent to-transparent pointer-events-none" />

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarCollapsed ? 80 : 260 }}
        className="relative z-10 h-full bg-void-900/80 backdrop-blur-xl border-r border-void-700/50 flex flex-col"
      >
        {/* Drag area for macOS */}
        <div className="h-8 drag-area" />

        {/* Logo */}
        <div className={`px-6 py-4 flex items-center gap-3 ${sidebarCollapsed ? 'justify-center' : ''}`}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neon-400 to-neon-600 flex items-center justify-center shadow-lg shadow-neon-500/20">
            <Shield className="w-6 h-6 text-void-950" />
          </div>
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="overflow-hidden"
              >
                <h1 className="font-display font-bold text-lg text-white whitespace-nowrap">
                  Intently
                </h1>
                <p className="text-xs text-void-400 whitespace-nowrap">Product Feature Analysis</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const Icon = item.icon

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  no-drag flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300
                  ${isActive
                    ? 'bg-neon-500/10 text-neon-400 border border-neon-500/30'
                    : 'text-void-300 hover:bg-void-800 hover:text-white'
                  }
                  ${sidebarCollapsed ? 'justify-center' : ''}
                `}
              >
                <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-neon-400' : ''}`} />
                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      className="font-medium whitespace-nowrap overflow-hidden"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            )
          })}
        </nav>

        {/* Backend Status */}
        <div className={`px-4 py-4 border-t border-void-700/50 ${sidebarCollapsed ? 'flex justify-center' : ''}`}>
          <div className={`flex items-center gap-3 ${sidebarCollapsed ? '' : ''}`}>
            <div className="relative">
              {isLoading ? (
                <Zap className="w-5 h-5 text-ember-400 animate-pulse" />
              ) : isConnected ? (
                <Circle className="w-4 h-4 fill-neon-400 text-neon-400" />
              ) : (
                <Circle className="w-4 h-4 fill-red-400 text-red-400" />
              )}
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="overflow-hidden"
                >
                  <p className="text-xs text-void-400 whitespace-nowrap">
                    {isLoading ? 'Connecting...' : isConnected ? 'Backend Online' : 'Backend Offline'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-6 h-6 rounded-full 
                     bg-void-800 border border-void-600 flex items-center justify-center
                     text-void-400 hover:text-white hover:border-neon-500/50 transition-all z-20 no-drag"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </motion.aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Drag area for macOS */}
        <div className="h-8 drag-area" />
        
        <div className="p-8 animate-in">
          {children}
        </div>
      </main>
    </div>
  )
}

