import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react'

interface BackendContextType {
  isConnected: boolean
  isLoading: boolean
  backendUrl: string
  error: string | null
  connectionAttempts: number
  startBackend: () => Promise<void>
  stopBackend: () => Promise<void>
  checkConnection: () => Promise<boolean>
}

const BackendContext = createContext<BackendContextType | null>(null)

// Configuration - OPTIMIZED for performance
const HEALTH_CHECK_INTERVAL_ACTIVE = 30000 // 30 seconds when window is active
const HEALTH_CHECK_INTERVAL_BACKGROUND = 120000 // 2 minutes when window is in background
const CONSECUTIVE_FAILURES_THRESHOLD = 2 // Require 2 failures before marking offline
const RECONNECT_DELAY = 10000 // Wait 10 seconds before reconnect attempt (was 3s)

export function BackendProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [backendUrl, setBackendUrl] = useState('http://127.0.0.1:8000')
  const [error, setError] = useState<string | null>(null)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  
  // Track consecutive failures to avoid flapping
  const consecutiveFailures = useRef(0)
  const lastSuccessTime = useRef<number>(0)
  const checkInProgress = useRef(false)

  const checkConnection = useCallback(async (): Promise<boolean> => {
    // Prevent overlapping checks
    if (checkInProgress.current) {
      return isConnected
    }
    
    checkInProgress.current = true
    
    try {
      const connected = await window.electronAPI?.checkBackend()
      
      if (connected) {
        consecutiveFailures.current = 0
        lastSuccessTime.current = Date.now()
        
        if (!isConnected) {
          setIsConnected(true)
          setError(null)
        }
        return true
      } else {
        consecutiveFailures.current++
        
        // Only mark as disconnected after consecutive failures
        // This prevents brief hiccups from showing "offline"
        if (consecutiveFailures.current >= CONSECUTIVE_FAILURES_THRESHOLD) {
          if (isConnected) {
            setIsConnected(false)
            setError('Backend connection lost. Attempting to reconnect...')
          }
        }
        return false
      }
    } catch (err) {
      consecutiveFailures.current++
      
      if (consecutiveFailures.current >= CONSECUTIVE_FAILURES_THRESHOLD) {
        if (isConnected) {
          setIsConnected(false)
          setError('Failed to reach backend server.')
        }
      }
      return false
    } finally {
      checkInProgress.current = false
    }
  }, [isConnected])

  const startBackend = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setConnectionAttempts(prev => prev + 1)
    consecutiveFailures.current = 0
    
    try {
      const started = await window.electronAPI?.startBackend()
      
      if (started) {
        // Wait a bit for the server to fully initialize
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        // Check connection with retries
        let attempts = 0
        const maxAttempts = 5
        
        while (attempts < maxAttempts) {
          const connected = await checkConnection()
          if (connected) {
            setIsConnected(true)
            setError(null)
            break
          }
          attempts++
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
        
        if (attempts >= maxAttempts) {
          setError('Backend started but not responding. Try again.')
        }
      } else {
        setError('Failed to start backend. Check Settings for correct paths.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error starting backend')
    } finally {
      setIsLoading(false)
    }
  }, [checkConnection])

  const stopBackend = useCallback(async () => {
    try {
      await window.electronAPI?.stopBackend()
      setIsConnected(false)
      consecutiveFailures.current = 0
      setError(null)
    } catch (err) {
      console.error('Failed to stop backend:', err)
    }
  }, [])

  // Initial connection check
  useEffect(() => {
    const init = async () => {
      const url = await window.electronAPI?.getBackendUrl()
      if (url) setBackendUrl(url)
      
      // Give a moment for everything to initialize
      await new Promise(resolve => setTimeout(resolve, 500))
      
      const connected = await checkConnection()
      if (!connected) {
        setError('Backend not running. Start it from Settings or it will auto-connect when available.')
      }
      setIsLoading(false)
    }
    init()
  }, [checkConnection])

  // Periodic health checks with smart interval - uses visibility API to reduce CPU when hidden
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null
    
    const getInterval = () => document.hidden 
      ? HEALTH_CHECK_INTERVAL_BACKGROUND 
      : HEALTH_CHECK_INTERVAL_ACTIVE
    
    const startHealthCheck = () => {
      if (intervalId) clearInterval(intervalId)
      intervalId = setInterval(async () => {
        // Skip check if document is hidden and we're connected
        if (document.hidden && isConnected) return
        
        const wasConnected = isConnected
        const nowConnected = await checkConnection()
        
        // If we just reconnected, show a success message briefly
        if (!wasConnected && nowConnected) {
          setError(null)
        }
      }, getInterval())
    }
    
    // Adjust interval when visibility changes
    const handleVisibilityChange = () => {
      startHealthCheck()
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    startHealthCheck()
    
    return () => {
      if (intervalId) clearInterval(intervalId)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [checkConnection, isConnected])

  // Listen for backend status changes from main process
  useEffect(() => {
    const handleStatusChange = (connected: boolean) => {
      if (connected) {
        consecutiveFailures.current = 0
        setIsConnected(true)
        setError(null)
      } else {
        setIsConnected(false)
        setError('Backend process stopped unexpectedly.')
      }
    }

    // Subscribe to backend status changes
    const cleanup = window.electronAPI?.onBackendStatusChanged?.(handleStatusChange)
    
    return () => {
      cleanup?.()
    }
  }, [])

  // Auto-reconnect when offline - with exponential backoff to reduce CPU usage
  useEffect(() => {
    if (!isConnected && !isLoading && consecutiveFailures.current > 0) {
      // Exponential backoff: 10s, 20s, 40s, max 60s
      const backoffDelay = Math.min(
        RECONNECT_DELAY * Math.pow(2, Math.min(consecutiveFailures.current - 1, 3)),
        60000
      )
      
      const reconnectTimer = setTimeout(async () => {
        // Skip if document is hidden to save resources
        if (document.hidden) return
        // Silent reconnect attempt
        await checkConnection()
      }, backoffDelay)
      
      return () => clearTimeout(reconnectTimer)
    }
  }, [isConnected, isLoading, checkConnection])

  return (
    <BackendContext.Provider
      value={{
        isConnected,
        isLoading,
        backendUrl,
        error,
        connectionAttempts,
        startBackend,
        stopBackend,
        checkConnection,
      }}
    >
      {children}
    </BackendContext.Provider>
  )
}

export function useBackend() {
  const context = useContext(BackendContext)
  if (!context) {
    throw new Error('useBackend must be used within BackendProvider')
  }
  return context
}
