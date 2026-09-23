import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { TopBar } from './TopBar'

interface Options {
  aboutOpen?: boolean
  started?: boolean
  nameAsHeading?: boolean
}

function setup({ aboutOpen = false, started = true, nameAsHeading = true }: Options = {}) {
  const onReset = vi.fn()
  const onToggleAbout = vi.fn()
  const onOpenBlog = vi.fn()
  render(
    <MemoryRouter>
      <TopBar
        name="NAME"
        started={started}
        nameAsHeading={nameAsHeading}
        aboutOpen={aboutOpen}
        onReset={onReset}
        onToggleAbout={onToggleAbout}
        onOpenBlog={onOpenBlog}
      />
    </MemoryRouter>,
  )
  return { onReset, onToggleAbout, onOpenBlog, user: userEvent.setup() }
}

describe('TopBar', () => {
  it('shows the name as the page heading', () => {
    setup()
    expect(screen.getByRole('heading', { level: 1, name: 'NAME' })).toBeInTheDocument()
  })

  it('shows the name as plain text on pages that have their own heading', () => {
    setup({ nameAsHeading: false })
    expect(screen.getByText('NAME')).toBeInTheDocument()
    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  })

  it('calls onReset from "start over"', async () => {
    const { onReset, user } = setup()
    await user.click(screen.getByRole('button', { name: 'start over' }))
    expect(onReset).toHaveBeenCalledOnce()
  })

  it('keeps the name and "start over" out of the way until a conversation has started', () => {
    setup({ started: false })

    expect(screen.queryByText('NAME')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'start over' })).not.toBeInTheDocument()
    // The blog link and the about button are always there.
    expect(screen.getByRole('link', { name: '✎ blog' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '◆ about me' })).toBeInTheDocument()
  })

  it('links to the writing page and tells the app when it is opened', async () => {
    const { onOpenBlog, user } = setup()
    const link = screen.getByRole('link', { name: '✎ blog' })

    expect(link).toHaveAttribute('href', '/writing')
    await user.click(link)
    expect(onOpenBlog).toHaveBeenCalledOnce()
  })

  it('toggles the about popover from the top-right button', async () => {
    const { onToggleAbout, user } = setup()
    await user.click(screen.getByRole('button', { name: '◆ about me' }))
    expect(onToggleAbout).toHaveBeenCalledOnce()
  })

  it('reflects the popover state in aria-expanded', () => {
    setup({ aboutOpen: true })
    expect(screen.getByRole('button', { name: '◆ about me' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('reports the popover as closed by default', () => {
    setup()
    expect(screen.getByRole('button', { name: '◆ about me' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })
})
