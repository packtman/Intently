/**
 * Tests for Collaboration Components
 * 
 * Tests cover:
 * - Phase 1: Finding Validation (FindingValidationPanel, ValidationStatusBadge)
 * - Phase 2: Comments System (CommentsThread, CommentCountBadge)
 * - Phase 3: Team Assignment (TeamAssignmentPanel, AssignmentBadge)
 * - Phase 4: Expert Feedback (ExpertFeedbackForm, FeedbackCountBadge)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { 
  FindingValidationPanel, 
  ValidationStatusBadge,
  CommentsThread,
  CommentCountBadge,
  TeamAssignmentPanel,
  AssignmentBadge,
  ExpertFeedbackForm,
  FeedbackCountBadge,
} from '../../components/collaboration'
import type { Finding } from '../../types'

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    getFindingValidation: vi.fn(),
    validateFinding: vi.fn(),
    getComments: vi.fn(),
    addComment: vi.fn(),
    getReviewAssignments: vi.fn(),
    assignFinding: vi.fn(),
    getFindingFeedback: vi.fn(),
    submitExpertFeedback: vi.fn(),
  },
}))

import { api } from '../../services/api'

// Test fixtures
const mockFinding: Finding = {
  id: 'finding-123',
  severity: 'high',
  title: 'Test Finding',
  description: 'This is a test finding',
  category: 'authentication',
  dimension: 'security',
  confidence: 'high',
  recommendation: 'Implement proper authentication',
}

const mockReviewId = 'review-456'

// Helper to wrap components with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('Phase 1: Finding Validation', () => {
  describe('ValidationStatusBadge', () => {
    it('renders pending status badge', () => {
      render(<ValidationStatusBadge status="pending" />)
      expect(screen.getByText('Pending')).toBeInTheDocument()
    })

    it('renders validated badge correctly', () => {
      render(<ValidationStatusBadge status="validated" />)
      expect(screen.getByText('Validated')).toBeInTheDocument()
    })

    it('renders rejected badge correctly', () => {
      render(<ValidationStatusBadge status="rejected" />)
      expect(screen.getByText('Rejected')).toBeInTheDocument()
    })

    it('renders needs_discussion badge correctly', () => {
      render(<ValidationStatusBadge status="needs_discussion" />)
      expect(screen.getByText('Needs Discussion')).toBeInTheDocument()
    })

    it('renders compact version without label', () => {
      const { container } = render(<ValidationStatusBadge status="validated" compact />)
      expect(container.querySelector('svg')).toBeInTheDocument()
      expect(screen.queryByText('Validated')).not.toBeInTheDocument()
    })
  })

  describe('FindingValidationPanel', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      vi.mocked(api.getFindingValidation).mockResolvedValue({ status: 'pending', validated: false })
    })

    it('does not render when disabled', () => {
      const { container } = render(
        <FindingValidationPanel
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={false}
        />,
        { wrapper: createWrapper() }
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders when enabled', () => {
      render(
        <FindingValidationPanel
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      expect(screen.getByText('Pending Validation')).toBeInTheDocument()
    })

    it('expands panel on click', async () => {
      render(
        <FindingValidationPanel
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      
      fireEvent.click(screen.getByText('Pending Validation'))
      await waitFor(() => {
        expect(screen.getByText('Validate Finding')).toBeInTheDocument()
      })
    })
  })
})

describe('Phase 2: Comments System', () => {
  describe('CommentCountBadge', () => {
    it('returns null for zero count', () => {
      const { container } = render(<CommentCountBadge count={0} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders count badge correctly', () => {
      render(<CommentCountBadge count={5} />)
      expect(screen.getByText('5')).toBeInTheDocument()
    })
  })

  describe('CommentsThread', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      vi.mocked(api.getComments).mockResolvedValue([])
    })

    it('does not render when disabled', () => {
      const { container } = render(
        <CommentsThread
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={false}
        />,
        { wrapper: createWrapper() }
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders when enabled', () => {
      render(
        <CommentsThread
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      expect(screen.getByText('Discussion')).toBeInTheDocument()
    })

    it('shows empty state when expanded with no comments', async () => {
      render(
        <CommentsThread
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      
      fireEvent.click(screen.getByText('Discussion'))
      await waitFor(() => {
        expect(screen.getByText('No comments yet')).toBeInTheDocument()
      })
    })
  })
})

describe('Phase 3: Team Assignment', () => {
  describe('AssignmentBadge', () => {
    it('renders security team badge correctly', () => {
      render(<AssignmentBadge team="security" />)
      expect(screen.getByText('Security')).toBeInTheDocument()
    })

    it('renders privacy team badge correctly', () => {
      render(<AssignmentBadge team="privacy" />)
      expect(screen.getByText('Privacy')).toBeInTheDocument()
    })

    it('returns null for unknown team', () => {
      const { container } = render(<AssignmentBadge team="unknown_team" />)
      expect(container.firstChild).toBeNull()
    })
  })

  describe('TeamAssignmentPanel', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      vi.mocked(api.getReviewAssignments).mockResolvedValue({
        review_id: mockReviewId,
        assignments: {},
        by_team: {},
      })
    })

    it('does not render when disabled', () => {
      const { container } = render(
        <TeamAssignmentPanel
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={false}
        />,
        { wrapper: createWrapper() }
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders when enabled', () => {
      render(
        <TeamAssignmentPanel
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      expect(screen.getByText('Team Assignment')).toBeInTheDocument()
    })

    it('shows team options when expanded', async () => {
      render(
        <TeamAssignmentPanel
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      
      fireEvent.click(screen.getByText('Team Assignment'))
      await waitFor(() => {
        expect(screen.getByText('Assign to Team')).toBeInTheDocument()
        expect(screen.getByText('Security')).toBeInTheDocument()
        expect(screen.getByText('Privacy')).toBeInTheDocument()
      })
    })
  })
})

describe('Phase 4: Expert Feedback', () => {
  describe('FeedbackCountBadge', () => {
    it('returns null for zero count', () => {
      const { container } = render(<FeedbackCountBadge count={0} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders count badge correctly', () => {
      render(<FeedbackCountBadge count={3} />)
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  describe('ExpertFeedbackForm', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      vi.mocked(api.getFindingFeedback).mockResolvedValue([])
    })

    it('does not render when disabled', () => {
      const { container } = render(
        <ExpertFeedbackForm
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={false}
        />,
        { wrapper: createWrapper() }
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders when enabled', () => {
      render(
        <ExpertFeedbackForm
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      expect(screen.getByText('Expert Feedback')).toBeInTheDocument()
    })

    it('shows feedback types when expanded', async () => {
      render(
        <ExpertFeedbackForm
          finding={mockFinding}
          reviewId={mockReviewId}
          enabled={true}
        />,
        { wrapper: createWrapper() }
      )
      
      fireEvent.click(screen.getByText('Expert Feedback'))
      await waitFor(() => {
        expect(screen.getByText('What would you like to correct?')).toBeInTheDocument()
        expect(screen.getByText('Accuracy')).toBeInTheDocument()
        expect(screen.getByText('Severity')).toBeInTheDocument()
        expect(screen.getByText('Recommendation')).toBeInTheDocument()
        expect(screen.getByText('Missing Context')).toBeInTheDocument()
      })
    })
  })
})

describe('Feature Flag Integration', () => {
  it('all components hidden when disabled', () => {
    render(
      <FindingValidationPanel finding={mockFinding} reviewId={mockReviewId} enabled={false} />,
      { wrapper: createWrapper() }
    )
    
    expect(screen.queryByText('Pending Validation')).not.toBeInTheDocument()
  })

  it('all components shown when enabled', () => {
    render(
      <>
        <FindingValidationPanel finding={mockFinding} reviewId={mockReviewId} enabled={true} />
        <CommentsThread finding={mockFinding} reviewId={mockReviewId} enabled={true} />
        <TeamAssignmentPanel finding={mockFinding} reviewId={mockReviewId} enabled={true} />
        <ExpertFeedbackForm finding={mockFinding} reviewId={mockReviewId} enabled={true} />
      </>,
      { wrapper: createWrapper() }
    )
    
    expect(screen.getByText('Pending Validation')).toBeInTheDocument()
    expect(screen.getByText('Discussion')).toBeInTheDocument()
    expect(screen.getByText('Team Assignment')).toBeInTheDocument()
    expect(screen.getByText('Expert Feedback')).toBeInTheDocument()
  })
})

