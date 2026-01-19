/**
 * Test Setup Configuration
 * 
 * This file configures the testing environment for the Intently Desktop app.
 * It sets up mocks for Electron APIs and browser APIs.
 */

import { vi, beforeAll, beforeEach, afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

// Mock window.electronAPI for all tests
const mockElectronAPI = {
  selectDirectory: vi.fn().mockResolvedValue(null),
  selectFile: vi.fn().mockResolvedValue(null),
  readFile: vi.fn().mockResolvedValue(null),
  saveFile: vi.fn().mockResolvedValue(null),
  getStore: vi.fn().mockResolvedValue(null),
  setStore: vi.fn().mockResolvedValue(true),
  getBackendUrl: vi.fn().mockResolvedValue('http://127.0.0.1:8000'),
  startBackend: vi.fn().mockResolvedValue(true),
  stopBackend: vi.fn().mockResolvedValue(true),
  checkBackend: vi.fn().mockResolvedValue(true),
  showNotification: vi.fn().mockResolvedValue(undefined),
  openExternal: vi.fn().mockResolvedValue(undefined),
  onPRDLoaded: vi.fn().mockReturnValue(() => {}),
  onCodebaseSelected: vi.fn().mockReturnValue(() => {}),
  onNewReview: vi.fn().mockReturnValue(() => {}),
  onOpenSettings: vi.fn().mockReturnValue(() => {}),
  onExportReport: vi.fn().mockReturnValue(() => {}),
  onBackendStatusChanged: vi.fn().mockReturnValue(() => {}),
}

// Create a proper fetch mock that returns a Response-like object
const createMockResponse = (data: unknown, ok = true, status = 200) => ({
  ok,
  status,
  json: () => Promise.resolve(data),
  text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data)),
})

beforeAll(() => {
  // Mock ResizeObserver (used by recharts)
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))
})

beforeEach(() => {
  // Reset and set up window.electronAPI mock for each test
  Object.defineProperty(window, 'electronAPI', {
    value: { ...mockElectronAPI },
    writable: true,
    configurable: true,
  })

  // Reset all mock implementations
  Object.keys(mockElectronAPI).forEach((key) => {
    const mock = mockElectronAPI[key as keyof typeof mockElectronAPI]
    if (typeof mock === 'function' && 'mockClear' in mock) {
      mock.mockClear()
    }
  })

  // Default fetch mock - returns empty array for reviews
  global.fetch = vi.fn().mockResolvedValue(createMockResponse([]))
})

afterEach(() => {
  vi.clearAllMocks()
})

export { mockElectronAPI, createMockResponse }

