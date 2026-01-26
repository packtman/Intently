import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  FolderOpen,
  Key,
  Zap,
  Save,
  Check,
  AlertCircle,
  RefreshCw,
  Terminal,
  Server,
  Play,
  Square,
} from 'lucide-react'
import { useBackend } from '../hooks/useBackend'

interface Settings {
  contextGraphPath: string
  pythonPath: string
  openaiApiKey: string
  anthropicApiKey: string
  autoStartBackend: boolean
}

export default function SettingsPage() {
  const { isConnected, isLoading, startBackend, stopBackend, checkConnection } = useBackend()
  const [settings, setSettings] = useState<Settings>({
    contextGraphPath: '',
    pythonPath: 'python3',
    openaiApiKey: '',
    anthropicApiKey: '',
    autoStartBackend: false,
  })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadSettings = async () => {
      const contextGraphPath = (await window.electronAPI?.getStore('contextGraphPath')) as string || ''
      const pythonPath = (await window.electronAPI?.getStore('pythonPath')) as string || 'python3'
      const openaiApiKey = (await window.electronAPI?.getStore('openaiApiKey')) as string || ''
      const anthropicApiKey = (await window.electronAPI?.getStore('anthropicApiKey')) as string || ''
      const autoStartBackend = (await window.electronAPI?.getStore('autoStartBackend')) as boolean || false

      setSettings({
        contextGraphPath,
        pythonPath,
        openaiApiKey,
        anthropicApiKey,
        autoStartBackend,
      })
    }
    loadSettings()
  }, [])

  const handleSave = async () => {
    try {
      await window.electronAPI?.setStore('contextGraphPath', settings.contextGraphPath.trim())
      await window.electronAPI?.setStore('pythonPath', settings.pythonPath.trim())
      // Trim API keys to avoid invalid key errors from whitespace
      await window.electronAPI?.setStore('openaiApiKey', settings.openaiApiKey.trim())
      await window.electronAPI?.setStore('anthropicApiKey', settings.anthropicApiKey.trim())
      await window.electronAPI?.setStore('autoStartBackend', settings.autoStartBackend)

      setSaved(true)
      setError(null)
      setTimeout(() => setSaved(false), 3000)

      window.electronAPI?.showNotification('Settings Saved', 'Your settings have been saved successfully.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    }
  }

  const selectContextGraphPath = async () => {
    const path = await window.electronAPI?.selectDirectory()
    if (path) {
      setSettings({ ...settings, contextGraphPath: path })
    }
  }

  const selectPythonPath = async () => {
    const path = await window.electronAPI?.selectFile([
      { name: 'Python', extensions: ['exe', ''] },
      { name: 'All Files', extensions: ['*'] },
    ])
    if (path) {
      setSettings({ ...settings, pythonPath: path })
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">Settings</h1>
        <p className="text-void-400 mt-2">Configure Intently Desktop</p>
      </div>

      {/* Backend Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card-glass rounded-2xl p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                isConnected ? 'bg-neon-500/20' : 'bg-red-500/20'
              }`}
            >
              <Server className={`w-6 h-6 ${isConnected ? 'text-neon-400' : 'text-red-400'}`} />
            </div>
            <div>
              <h2 className="font-display text-lg font-semibold text-white">Backend Server</h2>
              <p className={`text-sm ${isConnected ? 'text-neon-400' : 'text-red-400'}`}>
                {isLoading ? 'Connecting...' : isConnected ? 'Online' : 'Offline'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={checkConnection}
              disabled={isLoading}
              className="p-2 rounded-lg bg-void-800 border border-void-700 text-void-400 
                         hover:text-white hover:border-void-600 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            {isConnected ? (
              <button
                onClick={stopBackend}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30
                           text-red-400 hover:bg-red-500/20 transition-all"
              >
                <Square className="w-4 h-4" />
                Stop
              </button>
            ) : (
              <button
                onClick={startBackend}
                disabled={!settings.contextGraphPath}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-neon-500/10 border border-neon-500/30
                           text-neon-400 hover:bg-neon-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4" />
                Start
              </button>
            )}
          </div>
        </div>

        {!settings.contextGraphPath && (
          <div className="p-3 rounded-lg bg-ember-500/10 border border-ember-500/30 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-ember-400" />
            <p className="text-sm text-ember-300">
              Configure the Intently path below to start the backend server.
            </p>
          </div>
        )}
      </motion.div>

      {/* Path Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card-glass rounded-2xl p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-aurora-500/20 flex items-center justify-center">
            <FolderOpen className="w-5 h-5 text-aurora-400" />
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold text-white">Paths</h2>
            <p className="text-sm text-void-400">Configure installation paths</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-void-300 mb-2">
              Intently Installation Path
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={settings.contextGraphPath}
                onChange={(e) => setSettings({ ...settings, contextGraphPath: e.target.value })}
                placeholder="/path/to/Intently"
                className="input-field font-mono text-sm flex-1"
              />
              <button onClick={selectContextGraphPath} className="btn-secondary">
                Browse
              </button>
            </div>
            <p className="text-xs text-void-500 mt-1">
              Path to the Intently project directory (containing src/context_graph/)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-void-300 mb-2">Python Executable</label>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Terminal className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-void-500" />
                <input
                  type="text"
                  value={settings.pythonPath}
                  onChange={(e) => setSettings({ ...settings, pythonPath: e.target.value })}
                  placeholder="python3"
                  className="input-field pl-12 font-mono text-sm"
                />
              </div>
              <button onClick={selectPythonPath} className="btn-secondary">
                Browse
              </button>
            </div>
            <p className="text-xs text-void-500 mt-1">
              Path to Python 3.10+ executable (e.g., python3, /usr/bin/python3)
            </p>
          </div>
        </div>
      </motion.div>

      {/* API Keys */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card-glass rounded-2xl p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-neon-500/20 flex items-center justify-center">
            <Key className="w-5 h-5 text-neon-400" />
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold text-white">API Keys</h2>
            <p className="text-sm text-void-400">Configure AI provider API keys</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-void-300 mb-2">OpenAI API Key</label>
            <input
              type="password"
              value={settings.openaiApiKey}
              onChange={(e) => setSettings({ ...settings, openaiApiKey: e.target.value })}
              placeholder="sk-..."
              className="input-field font-mono text-sm"
            />
            <p className="text-xs text-void-500 mt-1">
              Get your key from{' '}
              <button
                onClick={() => window.electronAPI?.openExternal('https://platform.openai.com/api-keys')}
                className="text-neon-400 hover:underline"
              >
                platform.openai.com
              </button>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-void-300 mb-2">Anthropic API Key</label>
            <input
              type="password"
              value={settings.anthropicApiKey}
              onChange={(e) => setSettings({ ...settings, anthropicApiKey: e.target.value })}
              placeholder="sk-ant-..."
              className="input-field font-mono text-sm"
            />
            <p className="text-xs text-void-500 mt-1">
              Get your key from{' '}
              <button
                onClick={() => window.electronAPI?.openExternal('https://console.anthropic.com/settings/keys')}
                className="text-neon-400 hover:underline"
              >
                console.anthropic.com
              </button>
            </p>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-void-800/50 border border-void-700">
          <p className="text-xs text-void-400">
            API keys are stored locally on your machine and are never sent to external servers
            except when making requests to the respective AI providers.
          </p>
        </div>
      </motion.div>

      {/* Preferences */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card-glass rounded-2xl p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-ember-500/20 flex items-center justify-center">
            <Zap className="w-5 h-5 text-ember-400" />
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold text-white">Preferences</h2>
            <p className="text-sm text-void-400">Customize application behavior</p>
          </div>
        </div>

        <label className="flex items-center justify-between p-4 rounded-xl bg-void-800/50 border border-void-700 cursor-pointer hover:border-void-600 transition-all">
          <div>
            <p className="font-medium text-white">Auto-start Backend</p>
            <p className="text-sm text-void-400">Automatically start the backend server on launch</p>
          </div>
          <div className="relative">
            <input
              type="checkbox"
              checked={settings.autoStartBackend}
              onChange={(e) => setSettings({ ...settings, autoStartBackend: e.target.checked })}
              className="sr-only"
            />
            <div
              className={`
                w-14 h-8 rounded-full transition-colors
                ${settings.autoStartBackend ? 'bg-neon-500' : 'bg-void-700'}
              `}
            >
              <div
                className={`
                  w-6 h-6 rounded-full bg-white shadow-lg transition-transform mt-1
                  ${settings.autoStartBackend ? 'translate-x-7' : 'translate-x-1'}
                `}
              />
            </div>
          </div>
        </label>
      </motion.div>

      {/* Save Button */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-300">{error}</p>
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={handleSave} className="btn-primary flex items-center gap-2">
          {saved ? (
            <>
              <Check className="w-5 h-5" />
              Saved!
            </>
          ) : (
            <>
              <Save className="w-5 h-5" />
              Save Settings
            </>
          )}
        </button>
      </div>
    </div>
  )
}

