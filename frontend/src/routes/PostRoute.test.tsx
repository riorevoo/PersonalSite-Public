import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { detail, stubApi } from '../test/posts'
import { PostRoute } from './PostRoute'

function setup(path: string) {
  const onAsk = vi.fn()
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/writing/:slug"
          element={<PostRoute heading="WRITING" questions={['a question?']} onAsk={onAsk} />}
        />
      </Routes>
    </MemoryRouter>,
  )
  return { onAsk }
}

describe('PostRoute', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('says it is loading, then shows the post named in the address', async () => {
    vi.stubGlobal(
      'fetch',
      stubApi({ '/api/posts/the-pool': detail({ slug: 'the-pool', title: 'The pool' }) }),
    )
    setup('/writing/the-pool')

    expect(screen.getByRole('status')).toHaveTextContent('loading')
    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { level: 1, name: 'The pool' })).toBeInTheDocument()
  })

  it('passes a clicked question up to the app', async () => {
    vi.stubGlobal('fetch', stubApi({ '/api/posts/the-pool': detail({ slug: 'the-pool' }) }))
    const { onAsk } = setup('/writing/the-pool')

    await userEvent.setup().click(await screen.findByRole('button', { name: 'a question?' }))

    expect(onAsk).toHaveBeenCalledExactlyOnceWith('a question?')
  })

  it('says there is no post for an unknown address, with a way to all writing', async () => {
    vi.stubGlobal('fetch', stubApi({}))
    setup('/writing/nope')

    expect(await screen.findByText('There is no post at this address.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'NOT FOUND' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← all writing' })).toBeInTheDocument()
  })

  it('shows a friendly message when the post cannot be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    setup('/writing/the-pool')

    expect(await screen.findByText(/I could not load this post just now/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
  })
})
