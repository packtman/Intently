/**
 * Tests for PRDQualityScore Component
 * 
 * Tests cover:
 * - Loading state
 * - Score display
 * - Grade display
 * - Stats display
 * - Gaps display
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PRDQualityScore } from '../../../components/pm/PRDQualityScore'
import { api } from '../../../services/api'

vi.mock('../../../services/api', () => ({
  api: {
    getPRDQuality: vi.fn(),
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

describe('PRDQualityScore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.getPRDQuality).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <TestWrapper>
        <PRDQualityScore reviewId="review-1" />
      </TestWrapper>
    )

    expect(screen.getByText(/loading quality score/i)).toBeInTheDocument()
  })

  it('displays quality score and grade', async () => {
    const mockQuality = {
      score: 85,
      grade: 'B',
      gaps: ['Missing rate limiting section', 'No GDPR mention'],
      predicted_pushback: 2,
      blockers: 1,
      likely_questions: 3,
      possible_questions: 5,
    }

    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQuality)

    render(
      <TestWrapper>
        <PRDQualityScore reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('85')).toBeInTheDocument()
      expect(screen.getByText('B')).toBeInTheDocument()
      expect(screen.getByText(/out of 100/i)).toBeInTheDocument()
    })
  })

  it('displays stats correctly', async () => {
    const mockQuality = {
      score: 75,
      grade: 'C',
      gaps: [],
      predicted_pushback: 3,
      blockers: 2,
      likely_questions: 4,
      possible_questions: 6,
    }

    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQuality)

    render(
      <TestWrapper>
        <PRDQualityScore reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument() // Blockers
      expect(screen.getByText('4')).toBeInTheDocument() // Likely
      expect(screen.getByText('6')).toBeInTheDocument() // Possible
    })
  })

  it('displays gaps when present', async () => {
    const mockQuality = {
      score: 70,
      grade: 'C',
      gaps: ['Missing rate limiting section', 'No GDPR mention', 'No error handling'],
      predicted_pushback: 5,
      blockers: 3,
      likely_questions: 5,
      possible_questions: 7,
    }

    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQuality)

    render(
      <TestWrapper>
        <PRDQualityScore reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/key gaps/i)).toBeInTheDocument()
      expect(screen.getByText('Missing rate limiting section')).toBeInTheDocument()
      expect(screen.getByText('No GDPR mention')).toBeInTheDocument()
      expect(screen.getByText('No error handling')).toBeInTheDocument()
    })
  })

  it('does not display gaps section when no gaps', async () => {
    const mockQuality = {
      score: 95,
      grade: 'A',
      gaps: [],
      predicted_pushback: 0,
      blockers: 0,
      likely_questions: 0,
      possible_questions: 1,
    }

    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQuality)

    render(
      <TestWrapper>
        <PRDQualityScore reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.queryByText(/key gaps/i)).not.toBeInTheDocument()
    })
  })

  it('displays correct grade colors', async () => {
    const grades = [
      { grade: 'A', score: 95 },
      { grade: 'B', score: 85 },
      { grade: 'C', score: 75 },
      { grade: 'D', score: 65 },
      { grade: 'F', score: 50 },
    ]

    for (const { grade, score } of grades) {
      vi.mocked(api.getPRDQuality).mockResolvedValue({
        score,
        grade,
        gaps: [],
        predicted_pushback: 0,
        blockers: 0,
        likely_questions: 0,
        possible_questions: 0,
      })

      const { rerender } = render(
        <TestWrapper>
          <PRDQualityScore reviewId="review-1" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(grade)).toBeInTheDocument()
      })

      rerender(<div />) // Clean up for next iteration
    }
  })

  it('calls API with correct review ID', async () => {
    const mockQuality = {
      score: 80,
      grade: 'B',
      gaps: [],
      predicted_pushback: 1,
      blockers: 0,
      likely_questions: 2,
      possible_questions: 3,
    }

    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQuality)

    render(
      <TestWrapper>
        <PRDQualityScore reviewId="review-123" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(api.getPRDQuality).toHaveBeenCalledWith('review-123')
    })
  })
})
