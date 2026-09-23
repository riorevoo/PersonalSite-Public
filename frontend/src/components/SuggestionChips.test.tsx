import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SuggestionChips } from './SuggestionChips'

const suggestions = ['first question?', 'second question?']

describe('SuggestionChips', () => {
  it('renders one button per suggestion', () => {
    render(<SuggestionChips suggestions={suggestions} onPick={vi.fn()} />)
    expect(screen.getAllByRole('button')).toHaveLength(2)
    expect(screen.getByRole('group', { name: 'Suggested questions' })).toBeInTheDocument()
  })

  it('calls onPick with the chip text when clicked', async () => {
    const onPick = vi.fn()
    render(<SuggestionChips suggestions={suggestions} onPick={onPick} />)

    await userEvent.setup().click(screen.getByRole('button', { name: 'second question?' }))

    expect(onPick).toHaveBeenCalledExactlyOnceWith('second question?')
  })

  it('can be triggered from the keyboard', async () => {
    const onPick = vi.fn()
    render(<SuggestionChips suggestions={suggestions} onPick={onPick} />)

    const user = userEvent.setup()
    await user.tab()
    await user.keyboard('{Enter}')

    expect(onPick).toHaveBeenCalledExactlyOnceWith('first question?')
  })

  it('does nothing while disabled', async () => {
    const onPick = vi.fn()
    render(<SuggestionChips suggestions={suggestions} disabled onPick={onPick} />)

    const chip = screen.getByRole('button', { name: 'first question?' })
    expect(chip).toHaveAttribute('aria-disabled', 'true')
    await userEvent.setup().click(chip)

    expect(onPick).not.toHaveBeenCalled()
  })

  it('keeps keyboard focus on the chip that was just pressed while disabled', async () => {
    const onPick = vi.fn()
    const { rerender } = render(<SuggestionChips suggestions={suggestions} onPick={onPick} />)
    const user = userEvent.setup()

    await user.tab()
    await user.keyboard('{Enter}')
    rerender(<SuggestionChips suggestions={suggestions} disabled onPick={onPick} />)

    expect(screen.getByRole('button', { name: 'first question?' })).toHaveFocus()
    expect(onPick).toHaveBeenCalledOnce()
  })
})
