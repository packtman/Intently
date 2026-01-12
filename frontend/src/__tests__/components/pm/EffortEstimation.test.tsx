/**
 * Tests for EffortEstimation Component
 * 
 * Tests cover:
 * - Loading state
 * - Time range display
 * - Codebase support display
 * - Sprint estimate
 * - TLDR display
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EffortEstimation } from '../../../components/pm/EffortEstimation'
import { api } from '../../../services/api'

vi.mock('../../../services/api', () => ({
  api: {
    getEffortEstimation: vi.fn(),
  },
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('EffortEstimation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.getEffortEstimation).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    expect(screen.getByText(/loading effort estimation/i)).toBeInTheDocument()
  })

  it('displays time range correctly', async () => {
    const mockEstimation = {
      total_days: { min: 5, likely: 10, max: 15 },
      by_requirement: [],
      codebase_support: 75.5,
      tldr: 'Estimated 10 days with good codebase support',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // Min
      expect(screen.getByText('10')).toBeInTheDocument() // Likely
      expect(screen.getByText('15')).toBeInTheDocument() // Max
      expect(screen.getByText(/min days/i)).toBeInTheDocument()
      expect(screen.getByText(/likely days/i)).toBeInTheDocument()
      expect(screen.getByText(/max days/i)).toBeInTheDocument()
    })
  })

  it('displays codebase support percentage', async () => {
    const mockEstimation = {
      total_days: { min: 5, likely: 10, max: 15 },
      by_requirement: [],
      codebase_support: 80.5,
      tldr: 'Good support',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('81%')).toBeInTheDocument() // Rounded
      expect(screen.getByText(/codebase support/i)).toBeInTheDocument()
    })
  })

  it('displays TLDR summary', async () => {
    const mockEstimation = {
      total_days: { min: 5, likely: 10, max: 15 },
      by_requirement: [],
      codebase_support: 75.0,
      tldr: 'Estimated 10 days with good codebase support. Most patterns already exist.',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/summary/i)).toBeInTheDocument()
      expect(screen.getByText(mockEstimation.tldr)).toBeInTheDocument()
    })
  })

  it('displays sprint estimate when days > 0', async () => {
    const mockEstimation = {
      total_days: { min: 5, likely: 20, max: 30 },
      by_requirement: [],
      codebase_support: 60.0,
      tldr: '2 sprints estimated',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/sprint estimate/i)).toBeInTheDocument()
      expect(screen.getByText(/2 sprint/i)).toBeInTheDocument()
      expect(screen.getByText(/20 days/i)).toBeInTheDocument()
    })
  })

  it('displays singular sprint for 1 sprint', async () => {
    const mockEstimation = {
      total_days: { min: 3, likely: 8, max: 12 },
      by_requirement: [],
      codebase_support: 70.0,
      tldr: '1 sprint',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/1 sprint/i)).toBeInTheDocument()
      expect(screen.queryByText(/sprints/i)).not.toBeInTheDocument()
    })
  })

  it('calls API with correct review ID', async () => {
    const mockEstimation = {
      total_days: { min: 5, likely: 10, max: 15 },
      by_requirement: [],
      codebase_support: 75.0,
      tldr: 'Test',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-456" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(api.getEffortEstimation).toHaveBeenCalledWith('review-456')
    })
  })

  it('displays codebase support description', async () => {
    const mockEstimation = {
      total_days: { min: 5, likely: 10, max: 15 },
      by_requirement: [],
      codebase_support: 75.0,
      tldr: 'Test',
    }

    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)

    render(
      <TestWrapper>
        <EffortEstimation reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/percentage of patterns that already exist/i)).toBeInTheDocument()
    })
  })
})
