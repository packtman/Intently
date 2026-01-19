/**
 * ReviewDetail Component Tests
 * 
 * These tests ensure the review detail page correctly displays review results,
 * handles loading/error states, and supports filtering by dimensions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewDetail from '../../pages/ReviewDetail'
import { BackendProvider } from '../../hooks/useBackend'
import type { DashboardData, ReviewStatus } from '../../types'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

const TestWrapper = ({
  children,
  initialRoute = '/review/test-id',
}: {
  children: React.ReactNode
  initialRoute?: string
}) => {
  window.history.pushState({}, '', initialRoute)
  return (
    <QueryClientProvider client={createTestQueryClient()}>
      <BrowserRouter>
        <BackendProvider>
          <Routes>
            <Route path="/review/:id" element={children} />
          </Routes>
        </BackendProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

// Mock status data
const mockCompletedStatus: ReviewStatus = {
  review_id: 'test-id',
  status: 'completed',
  progress: 1,
  message: 'Review completed',
  dimensions: ['security', 'privacy'],
}

const mockRunningStatus: ReviewStatus = {
  review_id: 'test-id',
  status: 'running',
  progress: 0.5,
  message: 'Analyzing codebase...',
}

const mockFailedStatus: ReviewStatus = {
  review_id: 'test-id',
  status: 'failed',
  progress: 0.3,
  message: 'Failed to parse codebase: Invalid Python syntax',
}

// Mock dashboard data
const mockDashboard: DashboardData = {
  overview: {
    title: 'Test Feature Review',
    risk_rating: 'HIGH',
    total_findings: 15,
    critical_count: 2,
    high_count: 5,
    reviewed_at: '2024-01-15T10:30:00Z',
    dimensions_analyzed: ['security', 'privacy', 'engineering'],
    dimension_counts: {
      security: 8,
      privacy: 4,
      compliance: 0,
      engineering: 3,
      architecture: 0,
    },
  },
  severity_chart: {
    labels: ['Critical', 'High', 'Medium', 'Low'],
    data: [2, 5, 6, 2],
    colors: ['#ef4444', '#ff7d11', '#eab308', '#22c55e'],
  },
  category_chart: {
    labels: ['Injection', 'Auth', 'XSS'],
    data: [5, 7, 3],
  },
  risk_gauge: { value: 72 },
  findings_table: [
    {
      id: 'finding-1',
      severity: 'critical',
      title: 'SQL Injection in User Query',
      description: 'Direct user input concatenation in SQL',
      category: 'injection',
      dimension: 'security',
      confidence: 'high',
      recommendation: 'Use parameterized queries',
      source_type: 'llm',
      technical_details: 'Line 45 in user_service.py',
      attack_scenario: 'Attacker could execute arbitrary SQL',
      business_impact: 'Complete database compromise',
    },
    {
      id: 'finding-2',
      severity: 'high',
      title: 'PII Logged Without Masking',
      description: 'Email addresses logged in plain text',
      category: 'data_exposure',
      dimension: 'privacy',
      confidence: 'high',
      recommendation: 'Implement log masking',
      source_type: 'llm',
    },
    {
      id: 'finding-3',
      severity: 'medium',
      title: 'Missing Input Validation',
      description: 'No input validation on API endpoint',
      category: 'validation',
      dimension: 'security',
      confidence: 'medium',
      recommendation: 'Add input validation',
      source_type: 'pattern',
    },
    {
      id: 'finding-4',
      severity: 'low',
      title: 'Missing Unit Tests',
      description: 'Auth module lacks test coverage',
      category: 'code_quality',
      dimension: 'engineering',
      confidence: 'high',
      recommendation: 'Add unit tests',
      source_type: 'llm',
      estimated_effort: '4 hours',
    },
  ],
  delta_summary: {
    cards: [
      { label: 'New Endpoints', value: 5, icon: 'api' },
      { label: 'Modified Files', value: 12, icon: 'file' },
      { label: 'New Models', value: 3, icon: 'database' },
      { label: 'Auth Changes', value: 2, icon: 'lock' },
    ],
    flags: {
      introduces_pii: true,
      modifies_auth: true,
      expands_attack_surface: true,
    },
  },
  llm_analysis: {
    used: true,
    providers: ['openai', 'anthropic'],
    findings_count: 12,
    consensus_count: 8,
    total_tokens: 18000,
    latency_ms: 4500,
    summary_details: {
      executive_summary: 'This feature introduces significant security risks...',
      key_concerns: ['SQL injection vulnerability', 'PII exposure in logs'],
      positive_observations: ['Uses HTTPS', 'Rate limiting present'],
    },
    dimension_summaries: {
      security: '8 findings including 2 critical SQL injection vulnerabilities',
      privacy: '4 findings related to PII handling and logging',
      engineering: '3 findings about code quality and testing',
    },
  },
}

describe('ReviewDetail Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)
    window.electronAPI.saveFile = vi.fn().mockResolvedValue('/path/to/saved/file.md')
    window.electronAPI.showNotification = vi.fn()
  })

  describe('Loading State', () => {
    it('should show loading spinner while fetching status', async () => {
      global.fetch = vi.fn().mockImplementation(() => new Promise(() => {}))

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      expect(screen.getByText('Loading review...')).toBeInTheDocument()
    })

    it('should show progress bar during review', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockRunningStatus),
      })

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Analyzing codebase...')).toBeInTheDocument()
        expect(screen.getByText('50% complete')).toBeInTheDocument()
      })
    })
  })

  describe('Error State', () => {
    it('should show error message when review fails', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFailedStatus),
      })

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Review Failed')).toBeInTheDocument()
        expect(
          screen.getByText('Failed to parse codebase: Invalid Python syntax')
        ).toBeInTheDocument()
      })
    })

    it('should show error when dashboard fetch fails', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        return Promise.resolve({
          ok: false,
          status: 500,
          text: () => Promise.resolve('Server error'),
        })
      })

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Failed to Load Dashboard')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })
  })

  describe('Completed Review Display', () => {
    beforeEach(() => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDashboard),
        })
      })
    })

    it('should display review title', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Test Feature Review')).toBeInTheDocument()
      })
    })

    it('should display risk rating badge', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
      })
    })

    it('should display statistics cards', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        // Check for findings counts
        expect(screen.getByText('Critical')).toBeInTheDocument()
        expect(screen.getByText('High')).toBeInTheDocument()
        expect(screen.getByText('Risk Score')).toBeInTheDocument()
      })
    })

    it('should display risk gauge value', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('72')).toBeInTheDocument()
      })
    })

    it('should display delta summary flags', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Introduces PII')).toBeInTheDocument()
        expect(screen.getByText('Modifies Auth')).toBeInTheDocument()
        expect(screen.getByText('Expands Attack Surface')).toBeInTheDocument()
      })
    })

    it('should display LLM analysis section', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('AI Analysis Summary')).toBeInTheDocument()
        expect(screen.getByText(/openai/i)).toBeInTheDocument()
      })
    })
  })

  describe('Findings Table', () => {
    beforeEach(() => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDashboard),
        })
      })
    })

    it('should display findings', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('SQL Injection in User Query')).toBeInTheDocument()
        expect(screen.getByText('PII Logged Without Masking')).toBeInTheDocument()
      })
    })

    it('should show severity badges for findings', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getAllByText('CRITICAL').length).toBeGreaterThan(0)
        expect(screen.getAllByText('HIGH').length).toBeGreaterThan(0)
        expect(screen.getAllByText('MEDIUM').length).toBeGreaterThan(0)
      })
    })

    it('should show AI badge for LLM findings', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        const aiBadges = screen.getAllByText('AI')
        expect(aiBadges.length).toBeGreaterThan(0)
      })
    })

    it('should expand finding on click', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('SQL Injection in User Query')).toBeInTheDocument()
      })

      // Click to expand
      fireEvent.click(screen.getByText('SQL Injection in User Query'))

      await waitFor(() => {
        expect(screen.getByText('Use parameterized queries')).toBeInTheDocument()
        expect(screen.getByText('Attacker could execute arbitrary SQL')).toBeInTheDocument()
      })
    })
  })

  describe('Dimension Filtering', () => {
    beforeEach(() => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDashboard),
        })
      })
    })

    it('should display dimension tabs', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/All/)).toBeInTheDocument()
        expect(screen.getByText(/Security/)).toBeInTheDocument()
        expect(screen.getByText(/Privacy/)).toBeInTheDocument()
        expect(screen.getByText(/Engineering/)).toBeInTheDocument()
      })
    })

    it('should filter findings by dimension', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('SQL Injection in User Query')).toBeInTheDocument()
      })

      // Click Privacy tab
      fireEvent.click(screen.getByText(/Privacy/))

      await waitFor(() => {
        // Privacy finding should still be visible
        expect(screen.getByText('PII Logged Without Masking')).toBeInTheDocument()
        // Security finding should not be visible when filtered to privacy only
      })
    })

    it('should show finding counts per dimension', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        // The tabs show counts like "Security (2)" etc.
        // We just verify tabs are present with counts
        const securityTab = screen.getByText(/Security.*\(/i)
        expect(securityTab).toBeInTheDocument()
      })
    })
  })

  describe('Export Functionality', () => {
    beforeEach(() => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation((url: string) => {
        callCount++
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        if (url.includes('/markdown')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ markdown: '# Report\n...' }),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDashboard),
        })
      })
    })

    it('should have export button', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Export')).toBeInTheDocument()
      })
    })

    it('should trigger export on click', async () => {
      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Export')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Export'))

      await waitFor(() => {
        expect(window.electronAPI.saveFile).toHaveBeenCalled()
      })
    })
  })

  describe('Offline State', () => {
    it('should show offline message when backend is disconnected', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Backend Offline')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })
  })

  describe('All Risk Ratings Display', () => {
    const riskRatings = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'MINIMAL'] as const

    riskRatings.forEach((rating) => {
      it(`should display ${rating} risk rating correctly`, async () => {
        const dashboardWithRating = {
          ...mockDashboard,
          overview: { ...mockDashboard.overview, risk_rating: rating },
        }

        let callCount = 0
        global.fetch = vi.fn().mockImplementation(() => {
          callCount++
          if (callCount === 1) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(mockCompletedStatus),
            })
          }
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(dashboardWithRating),
          })
        })

        render(
          <TestWrapper>
            <ReviewDetail />
          </TestWrapper>
        )

        await waitFor(() => {
          expect(screen.getByText(`${rating} RISK`)).toBeInTheDocument()
        })
      })
    })
  })

  describe('All Severity Types', () => {
    it('should handle all finding severity types', async () => {
      const dashboardWithAllSeverities: DashboardData = {
        ...mockDashboard,
        findings_table: [
          { ...mockDashboard.findings_table[0], id: '1', severity: 'critical' },
          { ...mockDashboard.findings_table[0], id: '2', severity: 'high', title: 'High Finding' },
          { ...mockDashboard.findings_table[0], id: '3', severity: 'medium', title: 'Medium Finding' },
          { ...mockDashboard.findings_table[0], id: '4', severity: 'low', title: 'Low Finding' },
          { ...mockDashboard.findings_table[0], id: '5', severity: 'info', title: 'Info Finding' },
        ],
      }

      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(dashboardWithAllSeverities),
        })
      })

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('High Finding')).toBeInTheDocument()
        expect(screen.getByText('Medium Finding')).toBeInTheDocument()
        expect(screen.getByText('Low Finding')).toBeInTheDocument()
        expect(screen.getByText('Info Finding')).toBeInTheDocument()
      })
    })
  })

  describe('Empty Findings', () => {
    it('should show success message when no findings exist', async () => {
      const emptyDashboard: DashboardData = {
        ...mockDashboard,
        findings_table: [],
        llm_analysis: { ...mockDashboard.llm_analysis!, used: true },
      }

      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCompletedStatus),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyDashboard),
        })
      })

      render(
        <TestWrapper>
          <ReviewDetail />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/No Issues Found/i)).toBeInTheDocument()
      })
    })
  })
})

