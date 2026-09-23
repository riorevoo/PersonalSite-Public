import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { stubApi, summary } from '../test/posts'
import { WritingRoute } from './WritingRoute'

function setup() {
  render(
    <MemoryRouter>
      <WritingRoute heading="WRITING" intro="What I write." />
    </MemoryRouter>,
  )
}

describe('WritingRoute', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('says it is loading, then lists the posts', async () => {
    vi.stubGlobal('fetch', stubApi({ '/api/posts': [summary({ title: 'First post' })] }))
    setup()

    expect(screen.getByRole('status')).toHaveTextContent('loading')
    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'First post' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
  })

  it('shows a friendly message when the posts cannot be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    setup()

    expect(await screen.findByText(/I could not load the writing just now/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← back to asking' })).toBeInTheDocument()
  })
})
