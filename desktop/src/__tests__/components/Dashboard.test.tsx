/**
 * Dashboard Component Tests
 * 
 * These tests ensure the Dashboard page renders correctly and handles
 * different states (loading, empty, with data, offline).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from '../../pages/Dashboard'
import { BackendProvider } from '../../hooks/useBackend'
import type { Review } from '../../types'

// Create a fresh QueryClient for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    <BrowserRouter>
      <BackendProvider>{children}</BackendProvider>
    </BrowserRouter>
  </QueryClientProvider>
)

// Mock data
const mockReviews: Review[] = [
  {
    review_id: 'review-1',
    title: 'Authentication Feature Review',
    status: 'completed',
    risk_rating: 'HIGH',
    findings_count: 12,
    dimensions: ['security', 'privacy'],
    security_findings: 8,
    privacy_findings: 4,
    compliance_findings: 0,
    engineering_findings: 0,
    architecture_findings: 0,
    reviewed_at: '2024-01-15T10:30:00Z',
  },
  {
    review_id: 'review-2',
    title: 'Payment Integration Review',
    status: 'completed',
    risk_rating: 'CRITICAL',
    findings_count: 25,
    dimensions: ['security', 'compliance'],
    security_findings: 15,
    privacy_findings: 0,
    compliance_findings: 10,
    engineering_findings: 0,
    architecture_findings: 0,
    reviewed_at: '2024-01-10T14:00:00Z',
  },
  {
    review_id: 'review-3',
    title: 'User Profile Feature',
    status: 'completed',
    risk_rating: 'LOW',
    findings_count: 3,
    dimensions: ['security'],
    security_findings: 3,
    privacy_findings: 0,
    compliance_findings: 0,
    engineering_findings: 0,
    architecture_findings: 0,
    reviewed_at: '2024-01-05T09:00:00Z',
  },
]

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: backend connected
    window.electronAPI.checkBackend = vi.fn().mockResolvedValue(true)
  })

  describe('Rendering', () => {
    it('should render the dashboard header', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Product Dashboard')).toBeInTheDocument()
      })
    })

    it('should render the New Review button', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('New Review')).toBeInTheDocument()
      })
    })

    it('should render quick action cards', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Parse PRD')).toBeInTheDocument()
        expect(screen.getByText('Analyze Codebase')).toBeInTheDocument()
        expect(screen.getByText('Full Review')).toBeInTheDocument()
      })
    })
  })

  describe('Statistics Display', () => {
    it('should display correct statistics from reviews', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        // Total reviews: 3
        expect(screen.getByText('3')).toBeInTheDocument()
        // Critical: 1 (Payment Integration)
        expect(screen.getByText('1')).toBeInTheDocument()
      })
    })

    it('should show zero statistics when no reviews exist', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        const zeros = screen.getAllByText('0')
        expect(zeros.length).toBeGreaterThanOrEqual(4) // All stat cards show 0
      })
    })
  })

  describe('Review List', () => {
    it('should display recent reviews', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Authentication Feature Review')).toBeInTheDocument()
        expect(screen.getByText('Payment Integration Review')).toBeInTheDocument()
        expect(screen.getByText('User Profile Feature')).toBeInTheDocument()
      })
    })

    it('should display risk rating badges', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('HIGH')).toBeInTheDocument()
        expect(screen.getByText('CRITICAL')).toBeInTheDocument()
        expect(screen.getByText('LOW')).toBeInTheDocument()
      })
    })

    it('should display findings count for each review', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('12 findings')).toBeInTheDocument()
        expect(screen.getByText('25 findings')).toBeInTheDocument()
        expect(screen.getByText('3 findings')).toBeInTheDocument()
      })
    })

    it('should show "View all" link when more than 5 reviews', async () => {
      const manyReviews = Array(7)
        .fill(null)
        .map((_, i) => ({
          ...mockReviews[0],
          review_id: `review-${i}`,
          title: `Review ${i}`,
        }))

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(manyReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('View all')).toBeInTheDocument()
      })
    })

    it('should limit displayed reviews to 5', async () => {
      const manyReviews = Array(10)
        .fill(null)
        .map((_, i) => ({
          ...mockReviews[0],
          review_id: `review-${i}`,
          title: `Review Number ${i}`,
        }))

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(manyReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        // Should only show first 5 reviews
        expect(screen.getByText('Review Number 0')).toBeInTheDocument()
        expect(screen.getByText('Review Number 4')).toBeInTheDocument()
        expect(screen.queryByText('Review Number 5')).not.toBeInTheDocument()
      })
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no reviews exist', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('No reviews yet')).toBeInTheDocument()
        expect(screen.getByText('Create Review')).toBeInTheDocument()
      })
    })
  })

  describe('Offline State', () => {
    it('should show offline state when backend is disconnected', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Backend Offline')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })

    it('should show settings link in offline state', async () => {
      window.electronAPI.checkBackend = vi.fn().mockResolvedValue(false)

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(
        () => {
          expect(screen.getByText('Open Settings')).toBeInTheDocument()
        },
        { timeout: 5000 }
      )
    })
  })

  describe('Loading State', () => {
    it('should show loading indicator while fetching reviews', async () => {
      // Create a promise that never resolves to keep loading state
      global.fetch = vi.fn().mockImplementation(
        () =>
          new Promise(() => {
            // Never resolves
          })
      )

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      // Loading state should be shown initially
      expect(screen.getByText('Loading reviews...')).toBeInTheDocument()
    })
  })

  describe('Navigation Links', () => {
    it('should have correct href for New Review button', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        const newReviewLink = screen.getByText('New Review').closest('a')
        expect(newReviewLink).toHaveAttribute('href', '/new')
      })
    })

    it('should have correct href for review cards', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        const reviewLink = screen.getByText('Authentication Feature Review').closest('a')
        expect(reviewLink).toHaveAttribute('href', '/review/review-1')
      })
    })

    it('should have correct href for quick actions', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        const parsePRDLink = screen.getByText('Parse PRD').closest('a')
        expect(parsePRDLink).toHaveAttribute('href', '/new?step=prd')

        const analyzeLink = screen.getByText('Analyze Codebase').closest('a')
        expect(analyzeLink).toHaveAttribute('href', '/new?step=codebase')

        const fullReviewLink = screen.getByText('Full Review').closest('a')
        expect(fullReviewLink).toHaveAttribute('href', '/new')
      })
    })
  })

  describe('Dimensions Display', () => {
    it('should display review dimensions', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockReviews),
      })

      render(
        <TestWrapper>
          <Dashboard />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('security, privacy')).toBeInTheDocument()
        expect(screen.getByText('security, compliance')).toBeInTheDocument()
      })
    })
  })
})

