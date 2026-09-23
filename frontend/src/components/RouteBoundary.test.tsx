import { act, render, screen } from '@testing-library/react'
import { lazy } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RouteBoundary } from './RouteBoundary'

describe('RouteBoundary', () => {
  afterEach(() => vi.restoreAllMocks())

  it('announces loading and then displays the downloaded route', async () => {
    let finish: (module: { default: () => React.JSX.Element }) => void = () => {}
    const Page = lazy(
      () =>
        new Promise<{ default: () => React.JSX.Element }>((resolve) => {
          finish = resolve
        }),
    )
    render(
      <MemoryRouter>
        <RouteBoundary heading="WRITING" toWriting>
          <Page />
        </RouteBoundary>
      </MemoryRouter>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('loading')
    expect(screen.getByRole('link', { name: /all writing/ })).toBeInTheDocument()
    await act(async () => finish({ default: () => <h1>Downloaded post</h1> }))
    expect(screen.getByRole('heading', { name: 'Downloaded post' })).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('offers a real reload link after a chunk fails and resets on navigation', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const Broken = lazy(() => Promise.reject(new Error('Chunk failed')))
    const view = render(
      <MemoryRouter>
        <RouteBoundary key="broken" heading="WRITING" toWriting={false}>
          <Broken />
        </RouteBoundary>
      </MemoryRouter>,
    )
    const reload = await screen.findByRole('link', { name: 'Reload the page' })
    expect(reload).toHaveAttribute('href', window.location.href)
    expect(screen.getByRole('link', { name: /back to asking/ })).toBeInTheDocument()
    view.rerender(
      <MemoryRouter>
        <RouteBoundary key="next" heading="WRITING" toWriting={false}>
          <h1>Next page</h1>
        </RouteBoundary>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Next page' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Reload the page' })).not.toBeInTheDocument()
  })
})
