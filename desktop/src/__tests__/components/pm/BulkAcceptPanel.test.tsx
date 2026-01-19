/**
 * BulkAcceptPanel Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BulkAcceptPanel } from '../../../components/pm/BulkAcceptPanel'
import type { PRDChange } from '../../../types'

const mockChanges: PRDChange[] = [
  {
    id: 'change-1',
    section: 'Authentication',
    change_type: 'modification',
    current_text: 'Basic auth',
    suggested_text: 'OAuth',
    diff_hunks: [{ operation: 'add', content: 'OAuth', line_number: 1 }],
    reasoning: 'Security',
    team: 'security',
    severity: 'blocker',
    status: 'open',
  },
  {
    id: 'change-2',
    section: 'Rate Limiting',
    change_type: 'addition',
    current_text: '',
    suggested_text: 'Add limits',
    diff_hunks: [{ operation: 'add', content: 'Add limits', line_number: 5 }],
    reasoning: 'Performance',
    team: 'engineering',
    severity: 'likely',
    status: 'open',
  },
  {
    id: 'change-3',
    section: 'Logging',
    change_type: 'addition',
    current_text: '',
    suggested_text: 'Add logging',
    diff_hunks: [{ operation: 'add', content: 'Add logging', line_number: 10 }],
    reasoning: 'Debugging',
    team: 'engineering',
    severity: 'possible',
    status: 'open',
  },
]

const mockSummary = {
  total: 3,
  by_team: { security: 1, engineering: 2 },
  by_severity: { blocker: 1, likely: 1, possible: 1 },
}

describe('BulkAcceptPanel', () => {
  const defaultProps = {
    changes: mockChanges,
    summary: mockSummary,
    onClose: vi.fn(),
    onBulkAccept: vi.fn(),
  }

  it('renders panel with title', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    expect(screen.getByText('Select Changes to Accept')).toBeInTheDocument()
  })

  it('shows all changes', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.getByText('Rate Limiting')).toBeInTheDocument()
    expect(screen.getByText('Logging')).toBeInTheDocument()
  })

  it('shows selection count', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    expect(screen.getByText('0 of 3 selected')).toBeInTheDocument()
  })

  it('can select individual changes', async () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0])
    
    expect(screen.getByText('1 of 3 selected')).toBeInTheDocument()
  })

  it('can select all changes', async () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    const selectAllButton = screen.getByText('Select All')
    await userEvent.click(selectAllButton)
    
    expect(screen.getByText('3 of 3 selected')).toBeInTheDocument()
  })

  it('can clear selection', async () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    // Select all first
    await userEvent.click(screen.getByText('Select All'))
    expect(screen.getByText('3 of 3 selected')).toBeInTheDocument()
    
    // Clear selection
    await userEvent.click(screen.getByText('Clear Selection'))
    expect(screen.getByText('0 of 3 selected')).toBeInTheDocument()
  })

  it('shows quick filters by team', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    expect(screen.getByText(/security.*1/i)).toBeInTheDocument()
    expect(screen.getByText(/engineering.*2/i)).toBeInTheDocument()
  })

  it('shows blockers quick filter', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    expect(screen.getByText(/blockers.*1/i)).toBeInTheDocument()
  })

  it('filters by team when team button clicked', async () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    const securityButton = screen.getByText(/security.*1/i)
    await userEvent.click(securityButton)
    
    // Should select only security team changes
    expect(screen.getByText('1 of 3 selected')).toBeInTheDocument()
  })

  it('filters by blockers when blockers button clicked', async () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    const blockersButton = screen.getByText(/blockers.*1/i)
    await userEvent.click(blockersButton)
    
    expect(screen.getByText('1 of 3 selected')).toBeInTheDocument()
  })

  it('calls onClose when cancel clicked', async () => {
    const onClose = vi.fn()
    render(<BulkAcceptPanel {...defaultProps} onClose={onClose} />)
    
    await userEvent.click(screen.getByText('Cancel'))
    
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when X button clicked', async () => {
    const onClose = vi.fn()
    render(<BulkAcceptPanel {...defaultProps} onClose={onClose} />)
    
    const closeButtons = screen.getAllByRole('button')
    const xButton = closeButtons.find(btn => btn.querySelector('svg.w-5'))
    if (xButton) {
      await userEvent.click(xButton)
      expect(onClose).toHaveBeenCalled()
    }
  })

  it('calls onBulkAccept with selected IDs', async () => {
    const onBulkAccept = vi.fn()
    render(<BulkAcceptPanel {...defaultProps} onBulkAccept={onBulkAccept} />)
    
    // Select first change
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0])
    
    // Click accept
    await userEvent.click(screen.getByRole('button', { name: /accept selected/i }))
    
    expect(onBulkAccept).toHaveBeenCalledWith(['change-1'], undefined)
  })

  it('shows accept button with count', async () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    // Select two changes
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0])
    await userEvent.click(checkboxes[1])
    
    expect(screen.getByRole('button', { name: /accept selected.*2/i })).toBeInTheDocument()
  })

  it('disables accept button when nothing selected', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    const acceptButton = screen.getByRole('button', { name: /accept selected/i })
    expect(acceptButton).toBeDisabled()
  })

  it('shows severity badges on changes', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    expect(screen.getByText('blocker')).toBeInTheDocument()
    expect(screen.getByText('likely')).toBeInTheDocument()
    expect(screen.getByText('possible')).toBeInTheDocument()
  })

  it('shows team badges on changes', () => {
    render(<BulkAcceptPanel {...defaultProps} />)
    
    // Team badges in the change list
    const securityBadges = screen.getAllByText('security')
    expect(securityBadges.length).toBeGreaterThan(0)
  })

  it('closes on backdrop click', async () => {
    const onClose = vi.fn()
    render(<BulkAcceptPanel {...defaultProps} onClose={onClose} />)
    
    // Click on the backdrop (the outer div with onClick={onClose})
    const backdrop = screen.getByText('Select Changes to Accept').closest('.fixed')
    if (backdrop) {
      await userEvent.click(backdrop)
      expect(onClose).toHaveBeenCalled()
    }
  })
})
