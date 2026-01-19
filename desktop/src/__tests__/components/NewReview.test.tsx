/**
 * NewReview Component Tests
 * 
 * These tests ensure the review creation flow works correctly through all steps:
 * PRD input, codebase selection, configuration, and review submission.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import NewReview from '../../pages/NewReview'
import { BackendProvider } from '../../hooks/useBackend'
import type { ParsedIntent } from '../../types'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    <BrowserRouter>
      <BackendProvider>{children}</BackendProvider>
    </BrowserRouter>
  </QueryClientProvider>
)

// Mock parsed intent
const mockParsedIntent: ParsedIntent = {
  title: 'User Authentication Feature',
  summary: 'Implementing secure user authentication with OAuth2',
  features: ['Login', 'Logout', 'Password reset'],
  user_stories: ['As a user, I want to log in securely'],
  data_entities: [
    { name: 'User', type: 'model', is_sensitive: true },
    { name: 'Session', type: 'model', is_sensitive: true },
  ],
  api_changes: ['POST /api/auth/login', 'POST /api/auth/logout'],
  auth_requirements: ['JWT tokens', 'Refresh tokens'],
  external_integrations: ['OAuth provider'],
}

describe('NewReview Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)
    window.electronAPI.selectDirectory = vi.fn().mockResolvedValue(null)
    window.electronAPI.selectFile = vi.fn().mockResolvedValue(null)
    window.electronAPI.readFile = vi.fn().mockResolvedValue(null)
    window.electronAPI.getStore = vi.fn().mockResolvedValue(null)
    window.electronAPI.showNotification = vi.fn()
  })

  describe('Initial Rendering', () => {
    it('should render the page header', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('New Product Review')).toBeInTheDocument()
      })
    })

    it('should render progress steps', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('PRD')).toBeInTheDocument()
        expect(screen.getByText('Codebase')).toBeInTheDocument()
        expect(screen.getByText('Config')).toBeInTheDocument()
        expect(screen.getByText('Review')).toBeInTheDocument()
      })
    })

    it('should start on PRD step', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Product Requirement Document')).toBeInTheDocument()
      })
    })
  })

  describe('Offline State', () => {
    it('should show offline message when backend is disconnected', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)

      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Backend Required')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })
  })

  describe('Step 1: PRD Input', () => {
    it('should render title input', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g., User Authentication Feature')).toBeInTheDocument()
      })
    })

    it('should render PRD content textarea', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/# Feature Overview/)).toBeInTheDocument()
      })
    })

    it('should have Select File button', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Select File')).toBeInTheDocument()
      })
    })

    it('should disable Continue button when content is empty', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        const continueButton = screen.getByText('Continue')
        expect(continueButton).toBeDisabled()
      })
    })

    it('should enable Continue button when content is provided', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD\n\nSome content' } })

        const continueButton = screen.getByText('Continue')
        expect(continueButton).not.toBeDisabled()
      })
    })

    it('should trigger file selection dialog', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Select File'))
      })

      expect(window.electronAPI.selectFile).toHaveBeenCalled()
    })

    it('should show Preview Intent button when content is provided', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD' } })
      })

      expect(screen.getByText('Preview Intent')).toBeInTheDocument()
    })

    it('should parse intent when Preview Intent is clicked', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockParsedIntent),
      })

      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD\n\nContent' } })
      })

      fireEvent.click(screen.getByText('Preview Intent'))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/parse-prd'),
          expect.any(Object)
        )
      })
    })
  })

  describe('Step 2: Codebase Selection', () => {
    beforeEach(async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      // Navigate to step 2
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD' } })
      })

      fireEvent.click(screen.getByText('Continue'))
    })

    it('should render codebase path input', async () => {
      await waitFor(() => {
        expect(screen.getByPlaceholderText('/path/to/your/codebase')).toBeInTheDocument()
      })
    })

    it('should render Browse button', async () => {
      await waitFor(() => {
        expect(screen.getByText('Browse')).toBeInTheDocument()
      })
    })

    it('should render language selection options', async () => {
      await waitFor(() => {
        expect(screen.getByText('Python')).toBeInTheDocument()
        expect(screen.getByText('Kotlin')).toBeInTheDocument()
        expect(screen.getByText('TypeScript')).toBeInTheDocument()
        expect(screen.getByText('JavaScript')).toBeInTheDocument()
        expect(screen.getByText('YAML/OpenAPI')).toBeInTheDocument()
        expect(screen.getByText('JSON')).toBeInTheDocument()
      })
    })

    it('should have default languages selected', async () => {
      await waitFor(() => {
        // Default languages are python, kotlin, typescript
        const pythonButton = screen.getByText('Python').closest('button')
        expect(pythonButton?.className).toContain('neon')
      })
    })

    it('should toggle language selection', async () => {
      await waitFor(() => {
        const javascriptButton = screen.getByText('JavaScript').closest('button')
        fireEvent.click(javascriptButton!)

        // After clicking, JavaScript should be selected
        expect(javascriptButton?.className).toContain('neon')
      })
    })

    it('should trigger directory selection dialog', async () => {
      await waitFor(() => {
        fireEvent.click(screen.getByText('Browse'))
      })

      expect(window.electronAPI.selectDirectory).toHaveBeenCalled()
    })

    it('should have Back button', async () => {
      await waitFor(() => {
        expect(screen.getByText('Back')).toBeInTheDocument()
      })
    })

    it('should disable Continue when path is empty', async () => {
      await waitFor(() => {
        const continueButton = screen.getByText('Continue')
        expect(continueButton).toBeDisabled()
      })
    })

    it('should enable Continue when path is provided', async () => {
      await waitFor(() => {
        const pathInput = screen.getByPlaceholderText('/path/to/your/codebase')
        fireEvent.change(pathInput, { target: { value: '/Users/test/project' } })

        const continueButton = screen.getByText('Continue')
        expect(continueButton).not.toBeDisabled()
      })
    })
  })

  describe('Step 3: Configuration', () => {
    beforeEach(async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      // Navigate to step 3
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        const pathInput = screen.getByPlaceholderText('/path/to/your/codebase')
        fireEvent.change(pathInput, { target: { value: '/Users/test/project' } })
      })
      fireEvent.click(screen.getByText('Continue'))
    })

    it('should render analysis configuration section', async () => {
      await waitFor(() => {
        expect(screen.getByText('Analysis Configuration')).toBeInTheDocument()
      })
    })

    it('should render dimension selection', async () => {
      await waitFor(() => {
        expect(screen.getByText('Review Dimensions')).toBeInTheDocument()
        expect(screen.getByText('Security')).toBeInTheDocument()
        expect(screen.getByText('Privacy')).toBeInTheDocument()
        expect(screen.getByText('Compliance')).toBeInTheDocument()
        expect(screen.getByText('Engineering')).toBeInTheDocument()
        expect(screen.getByText('Architecture')).toBeInTheDocument()
      })
    })

    it('should have Security dimension selected by default', async () => {
      await waitFor(() => {
        const securityButton = screen.getByText('Security').closest('button')
        expect(securityButton?.className).toContain('neon') // Selected state
      })
    })

    it('should render LLM toggle', async () => {
      await waitFor(() => {
        expect(screen.getByText('AI-Powered Analysis')).toBeInTheDocument()
      })
    })

    it('should show API key fields when LLM is enabled', async () => {
      await waitFor(() => {
        expect(screen.getByText('API Keys')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('sk-...')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('sk-ant-...')).toBeInTheDocument()
      })
    })

    it('should allow toggling multiple dimensions', async () => {
      await waitFor(() => {
        const privacyButton = screen.getByText('Privacy').closest('button')
        fireEvent.click(privacyButton!)

        // Privacy should now be selected
        expect(privacyButton?.className).toContain('aurora')
      })
    })

    it('should not allow deselecting the last dimension', async () => {
      await waitFor(() => {
        // Only Security is selected by default, try to deselect it
        const securityButton = screen.getByText('Security').closest('button')

        // Button should be disabled when it's the last selected dimension
        expect(securityButton?.className).toContain('cursor-not-allowed')
      })
    })
  })

  describe('Step 4: Review Summary', () => {
    beforeEach(async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      // Navigate through all steps
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD' } })
        const titleInput = screen.getByPlaceholderText('e.g., User Authentication Feature')
        fireEvent.change(titleInput, { target: { value: 'Test Feature' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        const pathInput = screen.getByPlaceholderText('/path/to/your/codebase')
        fireEvent.change(pathInput, { target: { value: '/Users/test/project' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        expect(screen.getByText('Analysis Configuration')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Continue'))
    })

    it('should render review summary', async () => {
      await waitFor(() => {
        expect(screen.getByText('Review Summary')).toBeInTheDocument()
      })
    })

    it('should display PRD title in summary', async () => {
      await waitFor(() => {
        expect(screen.getByText('Test Feature')).toBeInTheDocument()
      })
    })

    it('should display codebase path in summary', async () => {
      await waitFor(() => {
        expect(screen.getByText('/Users/test/project')).toBeInTheDocument()
      })
    })

    it('should display selected dimensions', async () => {
      await waitFor(() => {
        expect(screen.getByText('Security')).toBeInTheDocument()
      })
    })

    it('should have Start Product Review button', async () => {
      await waitFor(() => {
        expect(screen.getByText('Start Product Review')).toBeInTheDocument()
      })
    })

    it('should submit review on button click', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            review_id: 'new-review-123',
            status: 'pending',
            message: 'Review started',
          }),
      })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Start Product Review'))
      })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/reviews'),
          expect.objectContaining({
            method: 'POST',
          })
        )
      })
    })

    it('should show loading state while submitting', async () => {
      global.fetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () => Promise.resolve({ review_id: 'test' }),
                }),
              1000
            )
          })
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Start Product Review'))
      })

      expect(screen.getByText('Starting Review...')).toBeInTheDocument()
    })

    it('should show error message on submission failure', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal server error'),
      })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Start Product Review'))
      })

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
      })
    })
  })

  describe('Navigation', () => {
    it('should navigate back from step 2 to step 1', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      // Go to step 2
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test PRD' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      // Go back
      await waitFor(() => {
        fireEvent.click(screen.getByText('Back'))
      })

      await waitFor(() => {
        expect(screen.getByText('Product Requirement Document')).toBeInTheDocument()
      })
    })

    it('should preserve PRD content when navigating back', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      const prdContent = '# My Test PRD\n\nThis is test content'

      // Fill in PRD
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: prdContent } })
      })

      // Go to step 2
      fireEvent.click(screen.getByText('Continue'))

      // Go back to step 1
      await waitFor(() => {
        fireEvent.click(screen.getByText('Back'))
      })

      // Content should be preserved
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/) as HTMLTextAreaElement
        expect(textarea.value).toBe(prdContent)
      })
    })
  })

  describe('File Loading', () => {
    it('should load file content when file is selected', async () => {
      const fileContent = '# PRD from File\n\nLoaded content'
      window.electronAPI.selectFile = vi.fn().mockResolvedValue('/path/to/prd.md')
      window.electronAPI.readFile = vi.fn().mockResolvedValue(fileContent)

      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Select File'))
      })

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/) as HTMLTextAreaElement
        expect(textarea.value).toBe(fileContent)
      })
    })

    it('should set title from filename', async () => {
      window.electronAPI.selectFile = vi.fn().mockResolvedValue('/path/to/my-feature-prd.md')
      window.electronAPI.readFile = vi.fn().mockResolvedValue('# Content')

      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      await waitFor(() => {
        fireEvent.click(screen.getByText('Select File'))
      })

      await waitFor(() => {
        const titleInput = screen.getByPlaceholderText(
          'e.g., User Authentication Feature'
        ) as HTMLInputElement
        expect(titleInput.value).toBe('my-feature-prd')
      })
    })
  })

  describe('API Keys', () => {
    it('should warn when LLM enabled without API keys', async () => {
      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      // Navigate to config step
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        const pathInput = screen.getByPlaceholderText('/path/to/your/codebase')
        fireEvent.change(pathInput, { target: { value: '/path' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        expect(screen.getByText('No API keys provided')).toBeInTheDocument()
      })
    })

    it('should show success message when API keys are provided', async () => {
      window.electronAPI.getStore = vi.fn().mockImplementation((key: string) => {
        if (key === 'openaiApiKey') return Promise.resolve('sk-test')
        if (key === 'anthropicApiKey') return Promise.resolve('sk-ant-test')
        return Promise.resolve(null)
      })

      render(
        <TestWrapper>
          <NewReview />
        </TestWrapper>
      )

      // Navigate to config step
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/# Feature Overview/)
        fireEvent.change(textarea, { target: { value: '# Test' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        const pathInput = screen.getByPlaceholderText('/path/to/your/codebase')
        fireEvent.change(pathInput, { target: { value: '/path' } })
      })
      fireEvent.click(screen.getByText('Continue'))

      await waitFor(() => {
        expect(screen.getByText('API key provided - AI analysis enabled')).toBeInTheDocument()
      })
    })
  })
})

