import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { usePost, usePosts } from './usePosts'

function stubFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('usePosts and usePost', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('usePosts loads the list', async () => {
    const posts = [{ slug: 'a', title: 'A' }]
    const fetchMock = stubFetch(posts)

    const { result } = renderHook(() => usePosts())

    await waitFor(() => expect(result.current).toEqual({ status: 'ready', data: posts }))
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/posts')
  })

  it('usePost loads one post by slug', async () => {
    const fetchMock = stubFetch({ slug: 'a-post', body: 'text' })

    const { result } = renderHook(() => usePost('a-post'))

    await waitFor(() => expect(result.current.status).toBe('ready'))
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/posts/a-post')
  })

  it('usePost reports an unknown slug as not-found', async () => {
    stubFetch({ detail: 'Post not found.' }, 404)

    const { result } = renderHook(() => usePost('nope'))

    await waitFor(() => expect(result.current).toEqual({ status: 'not-found' }))
  })

  it('usePosts reports a broken connection as an error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    const { result } = renderHook(() => usePosts())

    await waitFor(() => expect(result.current).toEqual({ status: 'error' }))
  })
})
