/**
 * Tests for PRDChangesView Component
 * 
 * Tests cover:
 * - Loading state
 * - Empty state
 * - Changes list rendering
 * - Accept/Reject mutations
 * - Bulk accept
 * - Undo functionality
 * - Download functionality
 * - Re-analyze functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PRDChangesView } from '../../../components/pm/PRDChangesView'
import { api } from '../../../services/api'

// Mock the API service
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

const mockChangesData = {
  changes: [
    {
      id: 'change-1',
      section: 'Authentication',
      change_type: 'addition',
      current_text: '',
      suggested_text: 'Add rate limiting',
      diff_hunks: [{ operation: 'add', content: 'Add rate limiting', line_number: 10 }],
      reasoning: 'Engineering will ask about this',
      team: 'engineering',
      severity: 'likely',
      status: 'open',
    },
    {
      id: 'change-2',
      section: 'Security',
      change_type: 'modification',
      current_text: 'Basic auth',
      suggested_text: 'OAuth 2.0',
      diff_hunks: [
        { operation: 'remove', content: 'Basic auth', line_number: 5 },
        { operation: 'add', content: 'OAuth 2.0', line_number: 6 },
      ],
      reasoning: 'Security team will push back',
      team: 'security',
      severity: 'blocker',
      status: 'open',
    },
  ],
  summary: {
    total: 2,
    by_team: { engineering: 1, security: 1 },
    by_severity: { blocker: 1, likely: 1 },
  },
}

describe('PRDChangesView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.getPRDChanges).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    expect(screen.getByText(/loading prd changes/i)).toBeInTheDocument()
  })

  it('shows empty state when no changes', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue({
      changes: [],
      summary: { total: 0, by_team: {}, by_severity: {} },
    })

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/no prd changes suggested/i)).toBeInTheDocument()
    })
  })

  it('renders changes list when changes exist', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
      expect(screen.getByText('Security')).toBeInTheDocument()
    })
  })

  it('displays summary statistics', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument() // Total
      expect(screen.getByText(/open changes/i)).toBeInTheDocument()
    })
  })

  it('calls accept mutation when change is accepted', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.acceptPRDChange).mockResolvedValue({
      applied: true,
      updated_prd: 'Updated PRD',
      change_summary: 'Change applied',
    })

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })

    // Find and click accept button (first change)
    const acceptButtons = screen.getAllByRole('button', { name: /accept/i })
    fireEvent.click(acceptButtons[0])

    await waitFor(() => {
      expect(api.acceptPRDChange).toHaveBeenCalledWith('review-1', 'change-1', undefined)
    })
  })

  it('calls reject mutation when change is rejected', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.rejectPRDChange).mockResolvedValue({ rejected: true })

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })

    const rejectButtons = screen.getAllByRole('button', { name: /reject/i })
    fireEvent.click(rejectButtons[0])

    await waitFor(() => {
      expect(api.rejectPRDChange).toHaveBeenCalledWith('review-1', 'change-1')
    })
  })

  it('opens bulk accept panel when bulk accept button is clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })

    const bulkAcceptButton = screen.getByRole('button', { name: /bulk accept/i })
    fireEvent.click(bulkAcceptButton)

    await waitFor(() => {
      expect(screen.getByText(/select changes to accept/i)).toBeInTheDocument()
    })
  })

  it('calls undo mutation when undo button is clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue({
      ...mockChangesData,
      changes: [
        ...mockChangesData.changes,
        { ...mockChangesData.changes[0], id: 'change-3', status: 'accepted' },
      ],
    })
    vi.mocked(api.undoLastChange).mockResolvedValue({
      reverted: true,
      restored_prd: 'Restored PRD',
    })

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })

    const undoButton = screen.getByRole('button', { name: /undo/i })
    fireEvent.click(undoButton)

    await waitFor(() => {
      expect(api.undoLastChange).toHaveBeenCalledWith('review-1')
    })
  })

  it('calls download mutation when download button is clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.downloadPRD).mockResolvedValue({
      content: 'PRD Content',
      filename: 'prd.md',
      content_type: 'text/markdown',
    })

    // Mock URL.createObjectURL and document.createElement
    global.URL.createObjectURL = vi.fn(() => 'blob:url')
    global.URL.revokeObjectURL = vi.fn()
    const mockClick = vi.fn()
    const mockCreateElement = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') {
        return { click: mockClick, href: '', download: '' } as any
      }
      return document.createElement(tag)
    })

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })

    const downloadButton = screen.getByRole('button', { name: /download/i })
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(api.downloadPRD).toHaveBeenCalledWith('review-1')
    })

    mockCreateElement.mockRestore()
  })

  it('calls re-analyze mutation when re-analyze button is clicked', async () => {
    vi.mocked(api.getPRDChanges).mockResolvedValue(mockChangesData)
    vi.mocked(api.reAnalyzePRD).mockResolvedValue({
      re_analyzed: true,
      new_predictions_count: 3,
      updated_quality_score: 85,
    })

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication')).toBeInTheDocument()
    })

    const reAnalyzeButton = screen.getByRole('button', { name: /re-analyze/i })
    fireEvent.click(reAnalyzeButton)

    await waitFor(() => {
      expect(api.reAnalyzePRD).toHaveBeenCalledWith('review-1')
    })
  })

  it('filters changes by status correctly', async () => {
    const dataWithMixedStatus = {
      ...mockChangesData,
      changes: [
        ...mockChangesData.changes,
        { ...mockChangesData.changes[0], id: 'change-3', status: 'accepted' },
        { ...mockChangesData.changes[0], id: 'change-4', status: 'rejected' },
      ],
    }

    vi.mocked(api.getPRDChanges).mockResolvedValue(dataWithMixedStatus)

    render(
      <TestWrapper>
        <PRDChangesView reviewId="review-1" />
      </TestWrapper>
    )

    await waitFor(() => {
      // Should show counts for open, accepted, rejected
      expect(screen.getByText(/2 open changes/i)).toBeInTheDocument()
      expect(screen.getByText(/1 accepted/i)).toBeInTheDocument()
      expect(screen.getByText(/1 rejected/i)).toBeInTheDocument()
    })
  })
})
