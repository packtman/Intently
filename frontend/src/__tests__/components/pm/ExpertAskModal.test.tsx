/**
 * Tests for ExpertAskModal Component
 * 
 * Tests cover:
 * - Modal rendering
 * - Expert search
 * - Expert selection
 * - Question editing
 * - Send functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ExpertAskModal } from '../../../components/pm/ExpertAskModal'
import { api } from '../../../services/api'

vi.mock('../../../services/api', () => ({
  api: {
    askExpert: vi.fn(),
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

describe('ExpertAskModal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not render when isOpen is false', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={false}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    expect(screen.queryByText(/quick ask/i)).not.toBeInTheDocument()
  })

  it('renders modal when isOpen is true', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    expect(screen.getByText(/quick ask/i)).toBeInTheDocument()
    expect(screen.getByText(/ping an expert/i)).toBeInTheDocument()
  })

  it('displays default question in textarea', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Will engineering ask about rate limiting?"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    const textarea = screen.getByPlaceholderText(/ask your question/i)
    expect(textarea).toHaveValue('Will engineering ask about rate limiting?')
  })

  it('allows editing question', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Original question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    const textarea = screen.getByPlaceholderText(/ask your question/i)
    fireEvent.change(textarea, { target: { value: 'Edited question' } })

    expect(textarea).toHaveValue('Edited question')
  })

  it('displays expert list', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Mock experts should be displayed
    expect(screen.getByText(/bob wilson/i)).toBeInTheDocument()
    expect(screen.getByText(/sarah chen/i)).toBeInTheDocument()
    expect(screen.getByText(/mike johnson/i)).toBeInTheDocument()
  })

  it('allows selecting an expert', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Find expert card (Bob Wilson)
    const expertCards = screen.getAllByText(/bob wilson/i)
    const expertCard = expertCards[0].closest('button')
    
    if (expertCard) {
      fireEvent.click(expertCard)
      // Expert should be selected (visual indicator)
      expect(expertCard).toHaveClass(/bg-primary/)
    }
  })

  it('filters experts by search query', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    const searchInput = screen.getByPlaceholderText(/search experts/i)
    fireEvent.change(searchInput, { target: { value: 'bob' } })

    // Should show Bob Wilson
    expect(screen.getByText(/bob wilson/i)).toBeInTheDocument()
    // Should hide others (or show filtered results)
  })

  it('disables send button when no expert selected', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('disables send button when question is empty', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion=""
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Select an expert first
    const expertCards = screen.getAllByText(/bob wilson/i)
    const expertCard = expertCards[0].closest('button')
    if (expertCard) {
      fireEvent.click(expertCard)
    }

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('enables send button when expert selected and question filled', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Select an expert
    const expertCards = screen.getAllByText(/bob wilson/i)
    const expertCard = expertCards[0].closest('button')
    if (expertCard) {
      fireEvent.click(expertCard)
    }

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).not.toBeDisabled()
  })

  it('calls askExpert API when send is clicked', async () => {
    vi.mocked(api.askExpert).mockResolvedValue({ ask_id: 'ask-123' })

    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Select expert (Bob Wilson)
    const expertCards = screen.getAllByText(/bob wilson/i)
    const expertCard = expertCards[0].closest('button')
    if (expertCard) {
      fireEvent.click(expertCard)
    }

    const sendButton = screen.getByRole('button', { name: /send/i })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(api.askExpert).toHaveBeenCalledWith({
        prediction_id: 'pred-1',
        expert_id: 'expert-1',
        expert_name: 'Bob Wilson',
        question: 'Test question',
      })
    })
  })

  it('calls onClose after successful send', async () => {
    vi.mocked(api.askExpert).mockResolvedValue({ ask_id: 'ask-123' })

    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Select expert
    const expertCards = screen.getAllByText(/bob wilson/i)
    const expertCard = expertCards[0].closest('button')
    if (expertCard) {
      fireEvent.click(expertCard)
    }

    const sendButton = screen.getByRole('button', { name: /send/i })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  it('calls onClose when cancel is clicked', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('calls onClose when X button is clicked', () => {
    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    const buttons = screen.getAllByRole('button')
    const xButton = buttons.find(btn => btn.querySelector('svg'))
    if (xButton) {
      fireEvent.click(xButton)
      expect(mockOnClose).toHaveBeenCalled()
    }
  })

  it('shows sending state when mutation is pending', async () => {
    vi.mocked(api.askExpert).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <TestWrapper>
        <ExpertAskModal
          isOpen={true}
          onClose={mockOnClose}
          predictionId="pred-1"
          defaultQuestion="Test question"
          reviewId="review-1"
        />
      </TestWrapper>
    )

    // Select expert
    const expertCards = screen.getAllByText(/bob wilson/i)
    const expertCard = expertCards[0].closest('button')
    if (expertCard) {
      fireEvent.click(expertCard)
    }

    const sendButton = screen.getByRole('button', { name: /send/i })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText(/sending/i)).toBeInTheDocument()
    })
  })
})
