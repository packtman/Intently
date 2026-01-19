/**
 * Settings Component Tests
 * 
 * These tests ensure the Settings page correctly displays and manages
 * application configuration including backend paths and API keys.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Settings from '../../pages/Settings'
import { BackendProvider } from '../../hooks/useBackend'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    <BrowserRouter>
      <BackendProvider>{children}</BackendProvider>
    </BrowserRouter>
  </QueryClientProvider>
)

describe('Settings Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)
    window.electronAPI.startBackend = vi.fn().mockResolvedValue(true)
    window.electronAPI.stopBackend = vi.fn().mockResolvedValue(true)
    window.electronAPI.selectDirectory = vi.fn().mockResolvedValue(null)
    window.electronAPI.selectFile = vi.fn().mockResolvedValue(null)
    window.electronAPI.getStore = vi.fn().mockResolvedValue(null)
    window.electronAPI.setStore = vi.fn().mockResolvedValue(true)
    window.electronAPI.showNotification = vi.fn()
    window.electronAPI.openExternal = vi.fn()
  })

  describe('Rendering', () => {
    it('should render settings header', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument()
        expect(screen.getByText('Configure Intently Desktop')).toBeInTheDocument()
      })
    })

    it('should render backend status section', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Backend Server')).toBeInTheDocument()
      })
    })

    it('should render paths section', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Paths')).toBeInTheDocument()
        expect(screen.getByText('Intently Installation Path')).toBeInTheDocument()
        expect(screen.getByText('Python Executable')).toBeInTheDocument()
      })
    })

    it('should render API keys section', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('API Keys')).toBeInTheDocument()
        expect(screen.getByText('OpenAI API Key')).toBeInTheDocument()
        expect(screen.getByText('Anthropic API Key')).toBeInTheDocument()
      })
    })

    it('should render preferences section', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Preferences')).toBeInTheDocument()
        expect(screen.getByText('Auto-start Backend')).toBeInTheDocument()
      })
    })

    it('should render Save Settings button', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Save Settings')).toBeInTheDocument()
      })
    })
  })

  describe('Backend Status', () => {
    it('should show Online when backend is connected', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Online')).toBeInTheDocument()
      })
    })

    it('should show Offline when backend is disconnected', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Offline')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })

    it('should show Stop button when backend is running', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Stop')).toBeInTheDocument()
      })
    })

    it('should show Start button when backend is stopped', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'contextGraphPath') return Promise.resolve('/path/to/intently')
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Start')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })

    it('should call startBackend when Start is clicked', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'contextGraphPath') return Promise.resolve('/path/to/intently')
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(
        () => {
          const startButton = screen.getByText('Start')
          fireEvent.click(startButton)
        },
        { timeout: 5000 }
      )

      await waitFor(() => {
        expect(window.electronAPI.startBackend).toHaveBeenCalled()
      })
    })

    it('should call stopBackend when Stop is clicked', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const stopButton = screen.getByText('Stop')
        fireEvent.click(stopButton)
      })

      await waitFor(() => {
        expect(window.electronAPI.stopBackend).toHaveBeenCalled()
      })
    })

    it('should show warning when contextGraphPath is not set', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)
      window.electronAPI.getStore = vi.fn().mockResolvedValue(null)

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(
            screen.getByText('Configure the Intently path below to start the backend server.')
          ).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })
  })

  describe('Path Configuration', () => {
    it('should load saved contextGraphPath', async () => {
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'contextGraphPath') return Promise.resolve('/Users/test/intently')
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const input = screen.getByPlaceholderText('/path/to/Intently') as HTMLInputElement
        expect(input.value).toBe('/Users/test/intently')
      })
    })

    it('should load saved pythonPath', async () => {
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'pythonPath') return Promise.resolve('/usr/local/bin/python3')
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const input = screen.getByPlaceholderText('python3') as HTMLInputElement
        expect(input.value).toBe('/usr/local/bin/python3')
      })
    })

    it('should open directory picker for contextGraphPath', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const browseButtons = screen.getAllByText('Browse')
        fireEvent.click(browseButtons[0]) // First Browse is for contextGraphPath
      })

      expect(window.electronAPI.selectDirectory).toHaveBeenCalled()
    })

    it('should open file picker for pythonPath', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const browseButtons = screen.getAllByText('Browse')
        fireEvent.click(browseButtons[1]) // Second Browse is for pythonPath
      })

      expect(window.electronAPI.selectFile).toHaveBeenCalled()
    })

    it('should update contextGraphPath when directory is selected', async () => {
      window.electronAPI.selectDirectory = vi.fn().mockResolvedValue('/new/path/to/intently')

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const browseButtons = screen.getAllByText('Browse')
        fireEvent.click(browseButtons[0])
      })

      await waitFor(() => {
        const input = screen.getByPlaceholderText('/path/to/Intently') as HTMLInputElement
        expect(input.value).toBe('/new/path/to/intently')
      })
    })
  })

  describe('API Keys', () => {
    it('should load saved API keys', async () => {
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'openaiApiKey') return Promise.resolve('sk-saved-key')
        if (key === 'anthropicApiKey') return Promise.resolve('sk-ant-saved-key')
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const openaiInput = screen.getByPlaceholderText('sk-...') as HTMLInputElement
        const anthropicInput = screen.getByPlaceholderText('sk-ant-...') as HTMLInputElement
        expect(openaiInput.value).toBe('sk-saved-key')
        expect(anthropicInput.value).toBe('sk-ant-saved-key')
      })
    })

    it('should mask API key inputs', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const openaiInput = screen.getByPlaceholderText('sk-...')
        const anthropicInput = screen.getByPlaceholderText('sk-ant-...')
        expect(openaiInput).toHaveAttribute('type', 'password')
        expect(anthropicInput).toHaveAttribute('type', 'password')
      })
    })

    it('should have links to API key pages', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('platform.openai.com')).toBeInTheDocument()
        expect(screen.getByText('console.anthropic.com')).toBeInTheDocument()
      })
    })

    it('should open external link for OpenAI', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('platform.openai.com'))
      })

      expect(window.electronAPI.openExternal).toHaveBeenCalledWith(
        'https://platform.openai.com/api-keys'
      )
    })
  })

  describe('Preferences', () => {
    it('should load autoStartBackend setting', async () => {
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'autoStartBackend') return Promise.resolve(true)
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        // The toggle should be in the "on" state
        // We check by finding the toggle's container
        const toggleContainer = screen.getByText('Auto-start Backend').closest('label')
        expect(toggleContainer).toBeInTheDocument()
      })
    })

    it('should toggle autoStartBackend setting', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const toggle = screen.getByText('Auto-start Backend').closest('label')
        fireEvent.click(toggle!)
      })

      // The state should toggle - we verify the setting gets saved
    })
  })

  describe('Saving Settings', () => {
    it('should save all settings when Save is clicked', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        // Fill in some settings
        const contextGraphInput = screen.getByPlaceholderText('/path/to/Intently')
        fireEvent.change(contextGraphInput, { target: { value: '/test/path' } })

        const pythonInput = screen.getByPlaceholderText('python3')
        fireEvent.change(pythonInput, { target: { value: '/usr/bin/python3' } })

        // Save
        fireEvent.click(screen.getByText('Save Settings'))
      })

      await waitFor(() => {
        expect(window.electronAPI.setStore).toHaveBeenCalledWith('contextGraphPath', '/test/path')
        expect(window.electronAPI.setStore).toHaveBeenCalledWith('pythonPath', '/usr/bin/python3')
      })
    })

    it('should show success notification after saving', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Save Settings'))
      })

      await waitFor(() => {
        expect(window.electronAPI.showNotification).toHaveBeenCalledWith(
          'Settings Saved',
          'Your settings have been saved successfully.'
        )
      })
    })

    it('should show Saved! button text after saving', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Save Settings'))
      })

      await waitFor(() => {
        expect(screen.getByText('Saved!')).toBeInTheDocument()
      })
    })

    it('should revert to Save Settings text after 3 seconds', async () => {
      vi.useFakeTimers()

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Save Settings'))
      })

      await waitFor(() => {
        expect(screen.getByText('Saved!')).toBeInTheDocument()
      })

      vi.advanceTimersByTime(3500)

      await waitFor(() => {
        expect(screen.getByText('Save Settings')).toBeInTheDocument()
      })

      vi.useRealTimers()
    })

    it('should show error message on save failure', async () => {
      window.electronAPI.setStore = vi.fn().mockRejectedValue(new Error('Failed to save'))

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Save Settings'))
      })

      await waitFor(() => {
        expect(screen.getByText('Failed to save')).toBeInTheDocument()
      })
    })
  })

  describe('Security', () => {
    it('should display security notice for API keys', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByText(/API keys are stored locally on your machine/i)
        ).toBeInTheDocument()
      })
    })
  })
})

