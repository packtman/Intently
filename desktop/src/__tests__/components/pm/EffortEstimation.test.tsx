/**
 * EffortEstimation Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EffortEstimation } from '../../../components/pm/EffortEstimation'
import { api } from '../../../services/api'
import type { EffortEstimation as EffortEstimationType } from '../../../types'

vi.mock('../../../services/api', () => ({
  api: {
    getEffortEstimation: vi.fn(),
  },
}))

const mockEstimation: EffortEstimationType = {
  total_days: {
    min: 15,
    likely: 25,
    max: 40,
  },
  by_requirement: [
    { title: 'Authentication', min_days: 5, likely_days: 8, max_days: 12, dimension: 'security' },
    { title: 'Rate Limiting', min_days: 3, likely_days: 5, max_days: 8, dimension: 'engineering' },
  ],
  codebase_support: 65,
  tldr: 'Medium complexity feature with good existing patterns. Recommend parallel development.',
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

describe('EffortEstimation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.getEffortEstimation).mockImplementation(() => new Promise(() => {}))
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    expect(screen.getByText('Loading effort estimation...')).toBeInTheDocument()
  })

  it('renders nothing when no data', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(null as any)
    
    const { container } = renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(container.querySelector('.bg-surface-900\\/50')).not.toBeInTheDocument()
    })
  })

  it('displays time estimates', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument() // min
      expect(screen.getByText('25')).toBeInTheDocument() // likely
      expect(screen.getByText('40')).toBeInTheDocument() // max
    })
  })

  it('displays time labels', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Min Days')).toBeInTheDocument()
      expect(screen.getByText('Likely Days')).toBeInTheDocument()
      expect(screen.getByText('Max Days')).toBeInTheDocument()
    })
  })

  it('displays TLDR summary', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument()
      expect(screen.getByText('Medium complexity feature with good existing patterns. Recommend parallel development.')).toBeInTheDocument()
    })
  })

  it('displays codebase support percentage', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Codebase Support')).toBeInTheDocument()
      expect(screen.getByText('65%')).toBeInTheDocument()
    })
  })

  it('displays sprint estimate', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Sprint Estimate')).toBeInTheDocument()
      // 25 likely days / 10 = ~3 sprints
      expect(screen.getByText(/~3 sprints/i)).toBeInTheDocument()
    })
  })

  it('shows singular sprint when estimate is 1', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue({
      ...mockEstimation,
      total_days: { min: 5, likely: 8, max: 10 },
    })
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText(/~1 sprint/i)).toBeInTheDocument()
    })
  })

  it('renders title', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Effort Estimation')).toBeInTheDocument()
    })
  })

  it('calls API with correct reviewId', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="test-review-456" />)
    
    await waitFor(() => {
      expect(api.getEffortEstimation).toHaveBeenCalledWith('test-review-456')
    })
  })

  it('displays codebase support explanation', async () => {
    vi.mocked(api.getEffortEstimation).mockResolvedValue(mockEstimation)
    
    renderWithProviders(<EffortEstimation reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Percentage of patterns that already exist in codebase')).toBeInTheDocument()
    })
  })
})
