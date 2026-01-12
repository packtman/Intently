/**
 * Tests for BulkAcceptPanel Component
 * 
 * Tests cover:
 * - Panel rendering
 * - Change selection
 * - Quick filters
 * - Bulk accept action
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BulkAcceptPanel } from '../../../components/pm/BulkAcceptPanel'
import type { PRDChange } from '../../../types'

const mockChanges: PRDChange[] = [
  {
    id: 'change-1',
    section: 'Authentication',
    change_type: 'addition',
    current_text: '',
    suggested_text: 'Add rate limiting',
    diff_hunks: [],
    reasoning: 'Engineering will ask',
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
    diff_hunks: [],
    reasoning: 'Security will push back',
    team: 'security',
    severity: 'blocker',
    status: 'open',
  },
  {
    id: 'change-3',
    section: 'Privacy',
    change_type: 'addition',
    current_text: '',
    suggested_text: 'Add GDPR section',
    diff_hunks: [],
    reasoning: 'Privacy team needs this',
    team: 'privacy',
    severity: 'possible',
    status: 'open',
  },
]

const mockSummary = {
  total: 3,
  by_team: { engineering: 1, security: 1, privacy: 1 },
  by_severity: { blocker: 1, likely: 1, possible: 1 },
}

describe('BulkAcceptPanel', () => {
  const mockOnClose = vi.fn()
  const mockOnBulkAccept = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders panel with changes list', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    expect(screen.getByText(/select changes to accept/i)).toBeInTheDocument()
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.getByText('Security')).toBeInTheDocument()
    expect(screen.getByText('Privacy')).toBeInTheDocument()
  })

  it('shows selection count', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    expect(screen.getByText(/0 of 3 selected/i)).toBeInTheDocument()
  })

  it('toggles change selection when checkbox is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    const firstCheckbox = checkboxes[0]

    expect(firstCheckbox).not.toBeChecked()
    fireEvent.click(firstCheckbox)
    expect(firstCheckbox).toBeChecked()
    expect(screen.getByText(/1 of 3 selected/i)).toBeInTheDocument()

    fireEvent.click(firstCheckbox)
    expect(firstCheckbox).not.toBeChecked()
    expect(screen.getByText(/0 of 3 selected/i)).toBeInTheDocument()
  })

  it('selects all changes when select all is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const selectAllButton = screen.getByRole('button', { name: /select all/i })
    fireEvent.click(selectAllButton)

    const checkboxes = screen.getAllByRole('checkbox')
    checkboxes.forEach(checkbox => {
      expect(checkbox).toBeChecked()
    })

    expect(screen.getByText(/3 of 3 selected/i)).toBeInTheDocument()
  })

  it('clears selection when clear selection is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    // Select all first
    const selectAllButton = screen.getByRole('button', { name: /select all/i })
    fireEvent.click(selectAllButton)

    // Then clear
    const clearButton = screen.getByRole('button', { name: /clear selection/i })
    fireEvent.click(clearButton)

    const checkboxes = screen.getAllByRole('checkbox')
    checkboxes.forEach(checkbox => {
      expect(checkbox).not.toBeChecked()
    })
  })

  it('filters by blockers when blockers quick filter is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const blockersButton = screen.getByRole('button', { name: /blockers \(1\)/i })
    fireEvent.click(blockersButton)

    // Should only show blocker change
    expect(screen.getByText('Security')).toBeInTheDocument()
    expect(screen.queryByText('Authentication')).not.toBeInTheDocument()
    expect(screen.queryByText('Privacy')).not.toBeInTheDocument()
  })

  it('filters by team when team quick filter is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const engineeringButton = screen.getByRole('button', { name: /engineering \(1\)/i })
    fireEvent.click(engineeringButton)

    // Should only show engineering change
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.queryByText('Security')).not.toBeInTheDocument()
    expect(screen.queryByText('Privacy')).not.toBeInTheDocument()
  })

  it('calls onBulkAccept with selected change IDs', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    // Select first two changes
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    fireEvent.click(checkboxes[1])

    const acceptButton = screen.getByRole('button', { name: /accept selected/i })
    fireEvent.click(acceptButton)

    expect(mockOnBulkAccept).toHaveBeenCalledWith(
      ['change-1', 'change-2'],
      undefined
    )
  })

  it('calls onBulkAccept with filter when using quick filter', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    // Use blockers filter
    const blockersButton = screen.getByRole('button', { name: /blockers \(1\)/i })
    fireEvent.click(blockersButton)

    const acceptButton = screen.getByRole('button', { name: /accept selected/i })
    fireEvent.click(acceptButton)

    expect(mockOnBulkAccept).toHaveBeenCalledWith(
      undefined,
      { severities: ['blocker'] }
    )
  })

  it('calls onClose when cancel button is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('calls onClose when X button is clicked', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const closeButton = screen.getByRole('button', { name: '' }) // X button
    const buttons = screen.getAllByRole('button')
    const xButton = buttons.find(btn => btn.querySelector('svg'))
    if (xButton) {
      fireEvent.click(xButton)
      expect(mockOnClose).toHaveBeenCalled()
    }
  })

  it('disables accept button when no changes selected', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const acceptButton = screen.getByRole('button', { name: /accept selected/i })
    expect(acceptButton).toBeDisabled()
  })

  it('enables accept button when changes are selected', () => {
    render(
      <BulkAcceptPanel
        changes={mockChanges}
        summary={mockSummary}
        onClose={mockOnClose}
        onBulkAccept={mockOnBulkAccept}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])

    const acceptButton = screen.getByRole('button', { name: /accept selected/i })
    expect(acceptButton).not.toBeDisabled()
  })
})
