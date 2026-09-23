import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { detail } from '../test/posts'
import { PostView } from './PostView'

function setup(post = detail(), questions = ['what do you build?', 'why backend?']) {
  const onAsk = vi.fn()
  render(
    <MemoryRouter>
      <PostView post={post} questions={questions} onAsk={onAsk} />
    </MemoryRouter>,
  )
  return { onAsk, user: userEvent.setup() }
}

describe('PostView', () => {
  it('shows the title as the page heading, with its summary', () => {
    setup(detail({ title: 'The pool', dek: 'A leak under retries.' }))

    expect(screen.getByRole('heading', { level: 1, name: 'The pool' })).toBeInTheDocument()
    expect(screen.getByText('A leak under retries.')).toBeInTheDocument()
  })

  it('shows the tag, date and reading time on one line', () => {
    setup(detail({ tag: 'postgres', date: '2026-08-14', read_minutes: 9 }))

    expect(screen.getByText('2026 · 08 · 14')).toHaveAttribute('datetime', '2026-08-14')
    const line = screen.getByText('2026 · 08 · 14').closest('p')
    expect(line).toHaveTextContent('postgres · 2026 · 08 · 14 · 9 min')
  })

  it('marks a draft', () => {
    setup(detail({ draft: true, tag: 'notes' }))
    expect(screen.getByText('2026 · 08 · 14').closest('p')).toHaveTextContent('draft · notes')
  })

  it('renders the Markdown body', () => {
    setup(detail({ body: 'Intro text.\n\n## Why it broke\nBecause of retries.' }))

    expect(screen.getByText('Intro text.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Why it broke' })).toBeInTheDocument()
  })

  it('offers a way to all writing and back to asking', () => {
    setup()

    expect(screen.getByRole('link', { name: '← all writing' })).toHaveAttribute('href', '/writing')
    expect(screen.getByRole('link', { name: '← back to asking' })).toHaveAttribute('href', '/')
  })

  it('offers the given questions under "ask about this" and asks the one clicked', async () => {
    const { onAsk, user } = setup()

    expect(screen.getByRole('complementary', { name: 'Ask about this post' })).toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(2)

    await user.click(screen.getByRole('button', { name: 'why backend?' }))

    expect(onAsk).toHaveBeenCalledExactlyOnceWith('why backend?')
  })
})
