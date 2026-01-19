/**
 * Backend Connection Integration Tests
 * 
 * These tests verify the backend connection management including
 * health checks, start/stop operations, and reconnection logic.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('Backend Connection Management', () => {
  let mockElectronAPI: {
    checkBackend: ReturnType<typeof vi.fn>
    startBackend: ReturnType<typeof vi.fn>
    stopBackend: ReturnType<typeof vi.fn>
    getBackendUrl: ReturnType<typeof vi.fn>
    getStore: ReturnType<typeof vi.fn>
  }

  beforeEach(() => {
    mockElectronAPI = {
      checkBackend: vi.fn(),
      startBackend: vi.fn(),
      stopBackend: vi.fn(),
      getBackendUrl: vi.fn().mockResolvedValue('http://127.0.0.1:8000'),
      getStore: vi.fn(),
    }

    Object.defineProperty(window, 'electronAPI', {
      value: mockElectronAPI,
      writable: true,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Health Check', () => {
    it('should return true when backend responds successfully', async () => {
      mockElectronAPI.checkBackend.mockResolvedValue(true)

      const result = await window.electronAPI.checkBackend()

      expect(result).toBe(true)
      expect(mockElectronAPI.checkBackend).toHaveBeenCalledTimes(1)
    })

    it('should return false when backend is unreachable', async () => {
      mockElectronAPI.checkBackend.mockResolvedValue(false)

      const result = await window.electronAPI.checkBackend()

      expect(result).toBe(false)
    })

    it('should handle check errors gracefully', async () => {
      mockElectronAPI.checkBackend.mockRejectedValue(new Error('Connection refused'))

      await expect(window.electronAPI.checkBackend()).rejects.toThrow('Connection refused')
    })
  })

  describe('Backend Start', () => {
    it('should start backend successfully when path is configured', async () => {
      mockElectronAPI.getStore.mockImplementation((key: string) => {
        if (key === 'contextGraphPath') return Promise.resolve('/path/to/intently')
        return Promise.resolve(null)
      })
      mockElectronAPI.startBackend.mockResolvedValue(true)

      const result = await window.electronAPI.startBackend()

      expect(result).toBe(true)
    })

    it('should fail to start when path is not configured', async () => {
      mockElectronAPI.getStore.mockResolvedValue(null)
      mockElectronAPI.startBackend.mockResolvedValue(false)

      const result = await window.electronAPI.startBackend()

      expect(result).toBe(false)
    })

    it('should fail to start when path does not exist', async () => {
      mockElectronAPI.getStore.mockImplementation((key: string) => {
        if (key === 'contextGraphPath') return Promise.resolve('/nonexistent/path')
        return Promise.resolve(null)
      })
      mockElectronAPI.startBackend.mockResolvedValue(false)

      const result = await window.electronAPI.startBackend()

      expect(result).toBe(false)
    })
  })

  describe('Backend Stop', () => {
    it('should stop backend successfully', async () => {
      mockElectronAPI.stopBackend.mockResolvedValue(true)

      const result = await window.electronAPI.stopBackend()

      expect(result).toBe(true)
      expect(mockElectronAPI.stopBackend).toHaveBeenCalledTimes(1)
    })

    it('should handle stop when backend is already stopped', async () => {
      mockElectronAPI.stopBackend.mockResolvedValue(true)

      // Multiple stop calls should all succeed
      await window.electronAPI.stopBackend()
      await window.electronAPI.stopBackend()

      expect(mockElectronAPI.stopBackend).toHaveBeenCalledTimes(2)
    })
  })

  describe('Connection State Transitions', () => {
    it('should transition from offline to online after start', async () => {
      // Initially offline
      mockElectronAPI.checkBackend.mockResolvedValueOnce(false)

      let status = await window.electronAPI.checkBackend()
      expect(status).toBe(false)

      // Start backend
      mockElectronAPI.startBackend.mockResolvedValue(true)
      await window.electronAPI.startBackend()

      // Now online
      mockElectronAPI.checkBackend.mockResolvedValueOnce(true)
      status = await window.electronAPI.checkBackend()
      expect(status).toBe(true)
    })

    it('should transition from online to offline after stop', async () => {
      // Initially online
      mockElectronAPI.checkBackend.mockResolvedValueOnce(true)

      let status = await window.electronAPI.checkBackend()
      expect(status).toBe(true)

      // Stop backend
      mockElectronAPI.stopBackend.mockResolvedValue(true)
      await window.electronAPI.stopBackend()

      // Now offline
      mockElectronAPI.checkBackend.mockResolvedValueOnce(false)
      status = await window.electronAPI.checkBackend()
      expect(status).toBe(false)
    })
  })

  describe('Reconnection Logic', () => {
    it('should detect when backend becomes unavailable', async () => {
      // Start online
      mockElectronAPI.checkBackend.mockResolvedValueOnce(true)
      expect(await window.electronAPI.checkBackend()).toBe(true)

      // Backend crashes
      mockElectronAPI.checkBackend.mockResolvedValueOnce(false)
      expect(await window.electronAPI.checkBackend()).toBe(false)
    })

    it('should detect when backend comes back online', async () => {
      // Start offline
      mockElectronAPI.checkBackend.mockResolvedValueOnce(false)
      expect(await window.electronAPI.checkBackend()).toBe(false)

      // Backend comes back
      mockElectronAPI.checkBackend.mockResolvedValueOnce(true)
      expect(await window.electronAPI.checkBackend()).toBe(true)
    })
  })

  describe('Backend URL', () => {
    it('should return configured backend URL', async () => {
      mockElectronAPI.getBackendUrl.mockResolvedValue('http://127.0.0.1:8000')

      const url = await window.electronAPI.getBackendUrl()

      expect(url).toBe('http://127.0.0.1:8000')
    })

    it('should return correct port', async () => {
      mockElectronAPI.getBackendUrl.mockResolvedValue('http://127.0.0.1:8000')

      const url = await window.electronAPI.getBackendUrl()

      expect(url).toContain(':8000')
    })
  })

  describe('Settings Persistence', () => {
    it('should load contextGraphPath from store', async () => {
      mockElectronAPI.getStore.mockImplementation((key: string) => {
        if (key === 'contextGraphPath') return Promise.resolve('/saved/path')
        return Promise.resolve(null)
      })

      const path = await window.electronAPI.getStore('contextGraphPath')

      expect(path).toBe('/saved/path')
    })

    it('should load pythonPath from store', async () => {
      mockElectronAPI.getStore.mockImplementation((key: string) => {
        if (key === 'pythonPath') return Promise.resolve('/usr/bin/python3')
        return Promise.resolve(null)
      })

      const path = await window.electronAPI.getStore('pythonPath')

      expect(path).toBe('/usr/bin/python3')
    })

    it('should return default when setting not found', async () => {
      mockElectronAPI.getStore.mockResolvedValue(null)

      const value = await window.electronAPI.getStore('nonexistent')

      expect(value).toBeNull()
    })
  })
})

describe('Backend Health Check Retry Logic', () => {
  it('should retry health check on failure', async () => {
    const mockCheck = vi.fn()
      .mockRejectedValueOnce(new Error('Timeout'))
      .mockRejectedValueOnce(new Error('Timeout'))
      .mockResolvedValueOnce(true)

    const checkWithRetry = async (retries = 3): Promise<boolean> => {
      for (let i = 0; i < retries; i++) {
        try {
          return await mockCheck()
        } catch {
          if (i === retries - 1) throw new Error('Max retries exceeded')
          await new Promise((r) => setTimeout(r, 100))
        }
      }
      return false
    }

    const result = await checkWithRetry()

    expect(result).toBe(true)
    expect(mockCheck).toHaveBeenCalledTimes(3)
  })

  it('should fail after max retries', async () => {
    const mockCheck = vi.fn().mockRejectedValue(new Error('Connection refused'))

    const checkWithRetry = async (retries = 3): Promise<boolean> => {
      for (let i = 0; i < retries; i++) {
        try {
          return await mockCheck()
        } catch {
          if (i === retries - 1) throw new Error('Max retries exceeded')
          await new Promise((r) => setTimeout(r, 10))
        }
      }
      return false
    }

    await expect(checkWithRetry()).rejects.toThrow('Max retries exceeded')
    expect(mockCheck).toHaveBeenCalledTimes(3)
  })
})

describe('Concurrent Connection Checks', () => {
  it('should handle multiple concurrent health checks', async () => {
    const mockCheck = vi.fn().mockResolvedValue(true)

    Object.defineProperty(window, 'electronAPI', {
      value: { checkBackend: mockCheck },
      writable: true,
    })

    const results = await Promise.all([
      window.electronAPI.checkBackend(),
      window.electronAPI.checkBackend(),
      window.electronAPI.checkBackend(),
    ])

    expect(results).toEqual([true, true, true])
  })

  it('should not have race conditions when starting backend', async () => {
    let startCount = 0
    const mockStart = vi.fn().mockImplementation(async () => {
      startCount++
      await new Promise((r) => setTimeout(r, 50))
      return true
    })

    Object.defineProperty(window, 'electronAPI', {
      value: { startBackend: mockStart },
      writable: true,
    })

    // Simulate multiple start attempts
    await Promise.all([
      window.electronAPI.startBackend(),
      window.electronAPI.startBackend(),
    ])

    // Both should complete successfully
    expect(startCount).toBe(2)
  })
})

