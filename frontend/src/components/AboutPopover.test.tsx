import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { profile } from '../content/profile'
import { AboutPopover } from './AboutPopover'

function setup() {
  const onClose = vi.fn()
  const triggerRef = createRef<HTMLButtonElement>()
  render(
    <>
      <button ref={triggerRef}>trigger</button>
      <p>outside content</p>
      <AboutPopover profile={profile} triggerRef={triggerRef} onClose={onClose} />
    </>,
  )
  return { onClose, user: userEvent.setup() }
}

describe('AboutPopover', () => {
  it('shows the short profile with facts and links', () => {
    setup()

    const dialog = screen.getByRole('dialog', { name: 'About me' })
    expect(dialog).toHaveTextContent(profile.name)
    expect(dialog).toHaveTextContent(profile.shortTagline)
    expect(dialog).toHaveTextContent(profile.shortBio)
    expect(screen.getAllByRole('term')).toHaveLength(profile.facts.length)
    expect(screen.getAllByRole('link')).toHaveLength(profile.links.length)
  })

  it('does not show a photo', () => {
    setup()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByText(/photo of me/i)).not.toBeInTheDocument()
  })

  it('moves focus into the popover when it opens', () => {
    setup()
    expect(screen.getByRole('dialog')).toHaveFocus()
  })

  it('closes and restores focus from the close button', async () => {
    const { onClose, user } = setup()
    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledExactlyOnceWith(true)
  })

  it('closes with Escape and restores focus when focus is inside', async () => {
    const { onClose, user } = setup()
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledExactlyOnceWith(true)
  })

  it('closes with Escape without stealing focus when focus is elsewhere', async () => {
    const { onClose, user } = setup()
    screen.getByRole('button', { name: 'trigger' }).focus()
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledExactlyOnceWith(false)
  })

  it('ignores other keys', async () => {
    const { onClose, user } = setup()
    await user.keyboard('a{Enter}')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('closes on a click outside, without restoring focus', async () => {
    const { onClose, user } = setup()
    await user.click(screen.getByText('outside content'))
    expect(onClose).toHaveBeenCalledExactlyOnceWith(false)
  })

  it('stays open when clicking inside', async () => {
    const { onClose, user } = setup()
    await user.click(screen.getByText(profile.shortBio))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('leaves clicks on the trigger to the trigger itself', async () => {
    const { onClose, user } = setup()
    await user.click(screen.getByRole('button', { name: 'trigger' }))
    expect(onClose).not.toHaveBeenCalled()
  })
})
