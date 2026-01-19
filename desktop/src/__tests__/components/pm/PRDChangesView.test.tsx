/**
 * PRDChangesView Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PRDChangesView } from '../../../components/pm/PRDChangesView'
import { api } from '../../../services/api'
import type { PRDChangesResponse } from '../../../types'

// Mock the API
vi.mock('../../../services/api', () => ({
  api: {
    getPRDChanges: vi.fn(),
    acceptPRDChange: vi.fn(),
    rejectPRDChange: vi.fn(),
    bulkAcceptChanges: vi.fn(),
    undoLastChange: vi.fn(),
    downloadPRD: vi.fn(),
    reAnalyzePRD: vi.fn(),
  },
}))

const mockChangesData: PRDChangesResponse = {
  changes: [
    {
      id: 'change-1',
      section: 'Authentication',
      change_type: 'modification',
      current_text: 'Basic auth',
      suggested_text: 'OAuth + Basic auth',
      diff_hunks: [
        { operation: 'remove', content: 'Basic auth', line_number: 1 },
        { operation: 'add', content: 'OAuth + Basic auth', line_number: 1 },
      ],
      reasoning: 'Security improvement',
      team: 'security',
      severity: 'blocker',
      status: 'open',
    },
    {
      id: 'change-2',
      section: 'Rate Limiting',
      change_type: 'addition',
      current_text: '',
      suggested_text: 'Add rate limiting section',
      diff_hunks: [
        { operation: 'add', content: 'Add rate limiting section', line_number: 5 },
      ],
      reasoning: 'Infrastructure requirement',
      team: 'engineering',
      severity: 'likely',
      status: 'open',
    },
  ],
  summary: {
    total: 2,
    by_team: { security: 1, engineering: 1 },
    by_severity: { blocker: 1, likely: 1 },
  },
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

describe('PRDChangesView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.getPRDChanges).mockImplementation(() => new Promise(() => {}))
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    expect(screen.getByText('Loading PRD changes...')).toBeInTheDocument()
  })

  it('shows empty state when no changes', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue({ changes: [], summary: { total: 0, by_team: {}, by_severity: {} } })
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('No PRD changes suggested')).toBeInTheDocument()
    })
  })

  it('renders changes list', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
      expect(screen.getByText('Rate Limiting')).toBeInTheDocument()
    })
  })

  it('shows summary statistics', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Total Changes')).toBeInTheDocument()
      expect(screen.getByText('Blockers')).toBeInTheDocument()
    })
  })

  it('calls acceptPRDChange when accepting', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.acceptPRDChange).mockResolvedValue({ applied: true, updated_prd: '', change_summary: '' })
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })
    
    const acceptButtons = screen.getAllByRole('button', { name: /^accept$/i })
    await userEvent.click(acceptButtons[0])
    
    await waitFor(() => {
      expect(api.acceptPRDChange).toHaveBeenCalledWith('review-1', 'change-1', undefined)
    })
  })

  it('calls rejectPRDChange when rejecting', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.rejectPRDChange).mockResolvedValue({ rejected: true })
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })
    
    const rejectButtons = screen.getAllByRole('button', { name: /reject/i })
    await userEvent.click(rejectButtons[0])
    
    await waitFor(() => {
      expect(api.rejectPRDChange).toHaveBeenCalledWith('review-1', 'change-1')
    })
  })

  it('opens bulk accept panel', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })
    
    const bulkAcceptButton = screen.getByRole('button', { name: /bulk accept/i })
    await userEvent.click(bulkAcceptButton)
    
    await waitFor(() => {
      expect(screen.getByText('Select Changes to Accept')).toBeInTheDocument()
    })
  })

  it('calls undoLastChange when undo clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue({
      ...mockChangesData,
      changes: mockChangesData.changes.map((c, i) => 
        i === 0 ? { ...c, status: 'accepted' as const } : c
      ),
    })
    vi.mocked(api.undoLastChange).mockResolvedValue({ reverted: true, restored_prd: '' })
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /undo/i })).toBeInTheDocument()
    })
  })

  it('calls downloadPRD when download clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.downloadPRD).mockResolvedValue({ content: 'PRD content', filename: 'prd.md', content_type: 'text/markdown' })
    
    // Mock URL.createObjectURL and URL.revokeObjectURL
    const mockCreateObjectURL = vi.fn(() => 'blob:url')
    const mockRevokeObjectURL = vi.fn()
    global.URL.createObjectURL = mockCreateObjectURL
    global.URL.revokeObjectURL = mockRevokeObjectURL
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })
    
    const downloadButton = screen.getByRole('button', { name: /download/i })
    await userEvent.click(downloadButton)
    
    await waitFor(() => {
      expect(api.downloadPRD).toHaveBeenCalledWith('review-1')
    })
  })

  it('calls reAnalyzePRD when re-analyze clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.reAnalyzePRD).mockResolvedValue({ re_analyzed: true, new_predictions_count: 3, updated_quality_score: 85 })
    
    renderWithProviders(<PRDChangesView reviewId="review-1" />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })
    
    const reAnalyzeButton = screen.getByRole('button', { name: /re-analyze/i })
    await userEvent.click(reAnalyzeButton)
    
    await waitFor(() => {
      expect(api.reAnalyzePRD).toHaveBeenCalledWith('review-1')
    })
  })

  it('triggers onAskExpert callback', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    const onAskExpert = vi.fn()
    
    renderWithProviders(<PRDChangesView reviewId="review-1" onAskExpert={onAskExpert} />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })
    
    const askExpertButtons = screen.getAllByRole('button', { name: /ask expert/i })
    await userEvent.click(askExpertButtons[0])
    
    expect(onAskExpert).toHaveBeenCalledWith('change-1', 'Security improvement')
  })
})
