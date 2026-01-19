/**
 * PRDQualityScore Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PRDQualityScore } from '../../../components/pm/PRDQualityScore'
import { api } from '../../../services/api'
import type { PRDQualityScore as PRDQualityScoreType } from '../../../types'

vi.mock('../../../services/api', () => ({
  api: {
    getPRDQuality: vi.fn(),
  },
}))

const mockQualityScore: PRDQualityScoreType = {
  score: 78,
  grade: 'B',
  gaps: ['Missing error handling section', 'No rollback strategy defined'],
  predicted_pushback: 3,
  blockers: 2,
  likely_questions: 5,
  possible_questions: 8,
}

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('PRDQualityScore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.getPRDQuality).mockImplementation(() => new Promise(() => {}))
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    expect(screen.getByText('Loading quality score...')).toBeInTheDocument()
  })

  it('renders nothing when no data', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(null as any)
    
    const { container } = renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(container.querySelector('.bg-surface-900\\/50')).not.toBeInTheDocument()
    })
  })

  it('displays score and grade', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQualityScore)
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('78')).toBeInTheDocument()
      expect(screen.getByText('B')).toBeInTheDocument()
    })
  })

  it('displays "out of 100" label', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQualityScore)
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('out of 100')).toBeInTheDocument()
    })
  })

  it('displays stats breakdown', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQualityScore)
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument() // blockers
      expect(screen.getByText('5')).toBeInTheDocument() // likely
      expect(screen.getByText('8')).toBeInTheDocument() // possible
      expect(screen.getByText('Blockers')).toBeInTheDocument()
      expect(screen.getByText('Likely')).toBeInTheDocument()
      expect(screen.getByText('Possible')).toBeInTheDocument()
    })
  })

  it('displays gaps list', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQualityScore)
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Key Gaps')).toBeInTheDocument()
      expect(screen.getByText('Missing error handling section')).toBeInTheDocument()
      expect(screen.getByText('No rollback strategy defined')).toBeInTheDocument()
    })
  })

  it('does not show gaps section when no gaps', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue({ ...mockQualityScore, gaps: [] })
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('78')).toBeInTheDocument()
    })
    
    expect(screen.queryByText('Key Gaps')).not.toBeInTheDocument()
  })

  it('calls API with correct reviewId', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQualityScore)
    
    renderWithProviders(<PRDQualityScore reviewId="test-review-123" />)
    
    await waitFor(() => {
      expect(api.getPRDQuality).toHaveBeenCalledWith('test-review-123')
    })
  })

  it('renders different grade colors', async () => {
    const grades = [
      { grade: 'A' as const, score: 95 },
      { grade: 'B' as const, score: 85 },
      { grade: 'C' as const, score: 75 },
      { grade: 'D' as const, score: 65 },
      { grade: 'F' as const, score: 50 },
    ]
    
    for (const { grade, score } of grades) {
      vi.mocked(api.getPRDQuality).mockResolvedValue({ ...mockQualityScore, grade, score })
      
      const { unmount } = renderWithProviders(<PRDQualityScore reviewId="review-1" />)
      
      await waitFor(() => {
        expect(screen.getByText(grade)).toBeInTheDocument()
      })
      
      unmount()
    }
  })

  it('renders title', async () => {
    vi.mocked(api.getPRDQuality).mockResolvedValue(mockQualityScore)
    
    renderWithProviders(<PRDQualityScore reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('PRD Quality Score')).toBeInTheDocument()
    })
  })
})
