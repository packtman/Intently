import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Shield, 
  Plus, 
  LayoutDashboard, 
  GitBranch,
  Zap 
} from 'lucide-react'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/new', icon: Plus, label: 'New Review' },
  ]

  return (
    <div className="min-h-screen grid-bg">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-surface-900/80 backdrop-blur-xl border-r border-surface-800 z-50">
        {/* Logo */}
        <div className="p-6 border-b border-surface-800">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -inset-1 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl blur opacity-30 group-hover:opacity-50 transition-opacity" />
            </div>
            <div>
              <h1 className="font-display font-bold text-lg text-white">Intently</h1>
              <p className="text-xs text-surface-400">Product Review</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                  ${isActive 
                    ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30' 
                    : 'text-surface-400 hover:text-white hover:bg-surface-800'
                  }
                `}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute left-0 w-1 h-8 bg-primary-500 rounded-r-full"
                  />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Status indicator */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-surface-800">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-surface-800/50">
            <div className="relative">
              <Zap className="w-5 h-5 text-primary-400" />
              <div className="absolute -inset-1 bg-primary-400 rounded-full blur-sm opacity-30 animate-pulse" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">LLM Ready</p>
              <p className="text-xs text-surface-400">OpenAI + Anthropic</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="p-8"
        >
          {children}
        </motion.div>
      </main>
    </div>
  )
}

