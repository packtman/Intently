import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react'

interface BackendContextType {
  isConnected: boolean
  isLoading: boolean
  backendUrl: string
  error: string | null
  connectionAttempts: number
  checkConnection: () => Promise<boolean>
}

const BackendContext = createContext<BackendContextType | null>(null)

// Configuration
const HEALTH_CHECK_INTERVAL_ACTIVE = 30000 // 30 seconds when window is active
const HEALTH_CHECK_INTERVAL_BACKGROUND = 120000 // 2 minutes when window is in background
const CONSECUTIVE_FAILURES_THRESHOLD = 2 // Require 2 failures before marking offline

// Default backend URL - can be overridden via environment
const DEFAULT_BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'

export function BackendProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [backendUrl] = useState(DEFAULT_BACKEND_URL)
  const [error, setError] = useState<string | null>(null)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  
  // Track consecutive failures to avoid flapping
  const consecutiveFailures = useRef(0)
  const checkInProgress = useRef(false)

  const checkConnection = useCallback(async (): Promise<boolean> => {
    // Prevent overlapping checks
    if (checkInProgress.current) {
      return isConnected
    }
    
    checkInProgress.current = true
    setConnectionAttempts(prev => prev + 1)
    
    try {
      const response = await fetch(`${backendUrl}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      })
      
      if (response.ok) {
        consecutiveFailures.current = 0
        
        if (!isConnected) {
          setIsConnected(true)
          setError(null)
        }
        return true
      } else {
        consecutiveFailures.current++
        
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
  }, [isConnected, backendUrl])

  // Initial connection check
  useEffect(() => {
    const init = async () => {
      // Give a moment for everything to initialize
      await new Promise(resolve => setTimeout(resolve, 500))
      
      const connected = await checkConnection()
      if (!connected) {
        setError('Backend not running. Start it with: npm run dev (in Context graph folder)')
      }
      setIsLoading(false)
    }
    init()
  }, [checkConnection])

  // Periodic health checks with smart interval
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

  return (
    <BackendContext.Provider
      value={{
        isConnected,
        isLoading,
        backendUrl,
        error,
        connectionAttempts,
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
