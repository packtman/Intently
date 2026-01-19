/**
 * ExpertAskModal Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('ExpertAskModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    predictionId: 'pred-1',
    defaultQuestion: 'Is this rate limiting approach correct?',
    reviewId: 'review-1',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing when closed', () => {
    const { container } = renderWithProviders(
      <ExpertAskModal {...defaultProps} isOpen={false} />
    )
    
    expect(container.firstChild).toBeNull()
  })

  it('renders modal when open', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    expect(screen.getByText('Quick Ask')).toBeInTheDocument()
  })

  it('shows default question', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const textarea = screen.getByPlaceholderText('Ask your question...')
    expect(textarea).toHaveValue('Is this rate limiting approach correct?')
  })

  it('can edit question', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const textarea = screen.getByPlaceholderText('Ask your question...')
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'New question')
    
    expect(textarea).toHaveValue('New question')
  })

  it('shows expert list', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
    expect(screen.getByText('Sarah Chen')).toBeInTheDocument()
    expect(screen.getByText('Mike Johnson')).toBeInTheDocument()
  })

  it('can select an expert', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const expertButton = screen.getByText('Bob Wilson').closest('button')
    await userEvent.click(expertButton!)
    
    // Expert should be selected - check for visual indicator
    expect(expertButton).toHaveClass('bg-primary-500/20')
  })

  it('can search experts', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const searchInput = screen.getByPlaceholderText('Search experts...')
    await userEvent.type(searchInput, 'Sarah')
    
    expect(screen.getByText('Sarah Chen')).toBeInTheDocument()
    expect(screen.queryByText('Bob Wilson')).not.toBeInTheDocument()
    expect(screen.queryByText('Mike Johnson')).not.toBeInTheDocument()
  })

  it('can search by domain', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const searchInput = screen.getByPlaceholderText('Search experts...')
    await userEvent.type(searchInput, 'security')
    
    expect(screen.getByText('Sarah Chen')).toBeInTheDocument()
    expect(screen.queryByText('Bob Wilson')).not.toBeInTheDocument()
  })

  it('can search by expertise', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const searchInput = screen.getByPlaceholderText('Search experts...')
    await userEvent.type(searchInput, 'rate limiting')
    
    expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
    expect(screen.queryByText('Sarah Chen')).not.toBeInTheDocument()
  })

  it('disables send button when no expert selected', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('disables send button when question is empty', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    // Select an expert
    const expertButton = screen.getByText('Bob Wilson').closest('button')
    await userEvent.click(expertButton!)
    
    // Clear the question
    const textarea = screen.getByPlaceholderText('Ask your question...')
    await userEvent.clear(textarea)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('enables send button when expert selected and question provided', async () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    // Select an expert
    const expertButton = screen.getByText('Bob Wilson').closest('button')
    await userEvent.click(expertButton!)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).not.toBeDisabled()
  })

  it('calls API when send clicked', async () => {
    vi.mocked(api.askExpert).mockResolvedValue({ ask_id: 'ask-1' })
    const onClose = vi.fn()
    
    renderWithProviders(<ExpertAskModal {...defaultProps} onClose={onClose} />)
    
    // Select an expert
    const expertButton = screen.getByText('Bob Wilson').closest('button')
    await userEvent.click(expertButton!)
    
    // Click send
    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)
    
    await waitFor(() => {
      expect(api.askExpert).toHaveBeenCalledWith({
        prediction_id: 'pred-1',
        expert_id: 'expert-1',
        expert_name: 'Bob Wilson',
        question: 'Is this rate limiting approach correct?',
      })
    })
  })

  it('closes modal after successful send', async () => {
    vi.mocked(api.askExpert).mockResolvedValue({ ask_id: 'ask-1' })
    const onClose = vi.fn()
    
    renderWithProviders(<ExpertAskModal {...defaultProps} onClose={onClose} />)
    
    // Select an expert
    const expertButton = screen.getByText('Bob Wilson').closest('button')
    await userEvent.click(expertButton!)
    
    // Click send
    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)
    
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('calls onClose when cancel clicked', async () => {
    const onClose = vi.fn()
    
    renderWithProviders(<ExpertAskModal {...defaultProps} onClose={onClose} />)
    
    await userEvent.click(screen.getByText('Cancel'))
    
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when X button clicked', async () => {
    const onClose = vi.fn()
    
    renderWithProviders(<ExpertAskModal {...defaultProps} onClose={onClose} />)
    
    const closeButtons = screen.getAllByRole('button')
    const xButton = closeButtons.find(btn => btn.querySelector('svg.w-5'))
    if (xButton) {
      await userEvent.click(xButton)
      expect(onClose).toHaveBeenCalled()
    }
  })

  it('shows expert domains', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    expect(screen.getByText('devops')).toBeInTheDocument()
    expect(screen.getByText('security')).toBeInTheDocument()
    expect(screen.getByText('engineering')).toBeInTheDocument()
  })

  it('shows expert expertise tags', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    expect(screen.getByText('rate limiting, infrastructure')).toBeInTheDocument()
    expect(screen.getByText('authentication, authorization')).toBeInTheDocument()
  })

  it('shows informational text about quick ask', () => {
    renderWithProviders(<ExpertAskModal {...defaultProps} />)
    
    expect(screen.getByText(/ping an expert for quick validation/i)).toBeInTheDocument()
    expect(screen.getByText(/not a formal review request/i)).toBeInTheDocument()
  })
})
