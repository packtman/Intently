/**
 * PRDChangeCard Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PRDChangeCard } from '../../../components/pm/PRDChangeCard'
import type { PRDChange } from '../../../types'

const mockChange: PRDChange = {
  id: 'change-1',
  section: 'Authentication Section',
  change_type: 'modification',
  current_text: 'Users can login with email',
  suggested_text: 'Users can login with email or OAuth providers (Google, GitHub)',
  diff_hunks: [
    { operation: 'remove', content: 'Users can login with email', line_number: 10 },
    { operation: 'add', content: 'Users can login with email or OAuth providers (Google, GitHub)', line_number: 10 },
  ],
  reasoning: 'OAuth login improves user experience and security',
  team: 'security',
  severity: 'blocker',
  status: 'open',
}

describe('PRDChangeCard', () => {
  const defaultProps = {
    change: mockChange,
    index: 1,
    total: 5,
    onAccept: vi.fn(),
    onReject: vi.fn(),
  }

  it('renders change section and severity', () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    expect(screen.getByText('Authentication Section')).toBeInTheDocument()
    expect(screen.getByText('BLOCKER')).toBeInTheDocument()
    expect(screen.getByText('security')).toBeInTheDocument()
  })

  it('shows change index out of total', () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    expect(screen.getByText('1 of 5')).toBeInTheDocument()
  })

  it('displays reasoning', () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    expect(screen.getByText('OAuth login improves user experience and security')).toBeInTheDocument()
  })

  it('shows diff hunks with correct styling', () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    // Check for removed content
    expect(screen.getByText('Users can login with email')).toBeInTheDocument()
    // Check for added content
    expect(screen.getByText('Users can login with email or OAuth providers (Google, GitHub)')).toBeInTheDocument()
  })

  it('calls onAccept when accept button clicked', async () => {
    const onAccept = vi.fn()
    render(<PRDChangeCard {...defaultProps} onAccept={onAccept} />)
    
    const acceptButton = screen.getByRole('button', { name: /accept/i })
    await userEvent.click(acceptButton)
    
    expect(onAccept).toHaveBeenCalledWith('change-1')
  })

  it('calls onReject when reject button clicked', async () => {
    const onReject = vi.fn()
    render(<PRDChangeCard {...defaultProps} onReject={onReject} />)
    
    const rejectButton = screen.getByRole('button', { name: /reject/i })
    await userEvent.click(rejectButton)
    
    expect(onReject).toHaveBeenCalledWith('change-1')
  })

  it('toggles edit mode', async () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    const editButton = screen.getByRole('button', { name: /edit/i })
    await userEvent.click(editButton)
    
    // Should show textarea in edit mode
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByText('Edit before accepting:')).toBeInTheDocument()
  })

  it('accepts with edited text', async () => {
    const onAccept = vi.fn()
    render(<PRDChangeCard {...defaultProps} onAccept={onAccept} />)
    
    // Enter edit mode
    const editButton = screen.getByRole('button', { name: /edit/i })
    await userEvent.click(editButton)
    
    // Edit the text
    const textarea = screen.getByRole('textbox')
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'Custom edited text')
    
    // Accept with edit
    const acceptButton = screen.getByRole('button', { name: /accept edited/i })
    await userEvent.click(acceptButton)
    
    expect(onAccept).toHaveBeenCalledWith('change-1', 'Custom edited text')
  })

  it('shows Ask Expert button when callback provided', () => {
    const onAskExpert = vi.fn()
    render(<PRDChangeCard {...defaultProps} onAskExpert={onAskExpert} />)
    
    expect(screen.getByRole('button', { name: /ask expert/i })).toBeInTheDocument()
  })

  it('does not show Ask Expert button when no callback', () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    expect(screen.queryByRole('button', { name: /ask expert/i })).not.toBeInTheDocument()
  })

  it('calls onAskExpert when clicked', async () => {
    const onAskExpert = vi.fn()
    render(<PRDChangeCard {...defaultProps} onAskExpert={onAskExpert} />)
    
    const askExpertButton = screen.getByRole('button', { name: /ask expert/i })
    await userEvent.click(askExpertButton)
    
    expect(onAskExpert).toHaveBeenCalledWith('change-1')
  })

  it('disables buttons when accepting', () => {
    render(<PRDChangeCard {...defaultProps} isAccepting={true} />)
    
    expect(screen.getByRole('button', { name: /accept/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /reject/i })).toBeDisabled()
  })

  it('disables buttons when rejecting', () => {
    render(<PRDChangeCard {...defaultProps} isRejecting={true} />)
    
    expect(screen.getByRole('button', { name: /accept/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /reject/i })).toBeDisabled()
  })

  it('can collapse and expand', async () => {
    render(<PRDChangeCard {...defaultProps} />)
    
    // Initially expanded - reasoning should be visible
    expect(screen.getByText('Why this change?')).toBeInTheDocument()
    
    // Find and click collapse button (the ChevronUp/ChevronDown button)
    const toggleButtons = screen.getAllByRole('button')
    const collapseButton = toggleButtons.find(btn => btn.querySelector('svg'))
    if (collapseButton) {
      await userEvent.click(collapseButton)
    }
  })

  it('renders different severity colors', () => {
    const { rerender } = render(<PRDChangeCard {...defaultProps} />)
    
    // Blocker - should have red styling
    expect(screen.getByText('BLOCKER')).toBeInTheDocument()
    
    // Change to likely
    rerender(<PRDChangeCard {...defaultProps} change={{ ...mockChange, severity: 'likely' }} />)
    expect(screen.getByText('LIKELY')).toBeInTheDocument()
    
    // Change to possible
    rerender(<PRDChangeCard {...defaultProps} change={{ ...mockChange, severity: 'possible' }} />)
    expect(screen.getByText('POSSIBLE')).toBeInTheDocument()
  })
})
