import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { REQUEST_TIMEOUT_MS } from '../constants'
import { useResource } from './useResource'

describe('useResource', () => {
  afterEach(() => vi.useRealTimers())

  it('ignores a stale success even when the loader ignores cancellation', async () => {
    let resolveFirst: (value: string) => void = () => {}
    const load = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<string>((resolve) => {
            resolveFirst = resolve
          }),
      )
      .mockResolvedValue('second')
    const { result, rerender } = renderHook(({ id }) => useResource<string>(id, load), {
      initialProps: { id: 'one' },
    })
    rerender({ id: 'two' })
    await waitFor(() => expect(result.current).toEqual({ status: 'ready', data: 'second' }))
    await act(async () => resolveFirst('stale'))
    expect(result.current).toEqual({ status: 'ready', data: 'second' })
  })

  it('ignores an older request when navigating back to the same key', async () => {
    let resolveFirst: (value: string) => void = () => {}
    const load = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<string>((resolve) => {
            resolveFirst = resolve
          }),
      )
      .mockResolvedValue('latest')
    const { result, rerender } = renderHook(({ id }) => useResource<string>(id, load), {
      initialProps: { id: 'one' },
    })
    rerender({ id: 'two' })
    rerender({ id: 'one' })
    await waitFor(() => expect(result.current).toEqual({ status: 'ready', data: 'latest' }))
    await act(async () => resolveFirst('stale'))
    expect(result.current).toEqual({ status: 'ready', data: 'latest' })
  })

  it('times out hung loads and ignores a subsequent success', async () => {
    vi.useFakeTimers()
    let signalSeen: AbortSignal | undefined
    let resolveLoad: (value: string) => void = () => {}
    const load = vi.fn((signal: AbortSignal) => {
      signalSeen = signal
      return new Promise<string>((resolve) => {
        resolveLoad = resolve
      })
    })
    const { result } = renderHook(() => useResource('one', load))
    await act(async () => vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS))
    expect(signalSeen?.aborted).toBe(true)
    expect(result.current).toEqual({ status: 'error' })
    await act(async () => resolveLoad('late'))
    expect(result.current).toEqual({ status: 'error' })
    expect(vi.getTimerCount()).toBe(0)
  })

  it('clears the timer after success and on unmount', async () => {
    vi.useFakeTimers()
    const load = vi.fn().mockResolvedValue('done')
    const first = renderHook(() => useResource('one', load))
    await act(async () => {})
    expect(first.result.current.status).toBe('ready')
    expect(vi.getTimerCount()).toBe(0)
    first.unmount()
    const pending = vi.fn(() => new Promise<string>(() => {}))
    const second = renderHook(() => useResource('two', pending))
    expect(vi.getTimerCount()).toBe(1)
    second.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
  it('starts loading, then delivers the data', async () => {
    const load = vi.fn().mockResolvedValue(['a'])
    const { result } = renderHook(() => useResource('key', load))

    expect(result.current).toEqual({ status: 'loading' })
    await waitFor(() => expect(result.current).toEqual({ status: 'ready', data: ['a'] }))
  })

  it('reports a 404 as not-found', async () => {
    const load = vi.fn().mockRejectedValue(new ApiError(404, 'GET /x failed: 404'))
    const { result } = renderHook(() => useResource('key', load))

    await waitFor(() => expect(result.current).toEqual({ status: 'not-found' }))
  })

  it('reports any other failure as an error', async () => {
    const load = vi.fn().mockRejectedValue(new ApiError(500, 'GET /x failed: 500'))
    const { result } = renderHook(() => useResource('key', load))

    await waitFor(() => expect(result.current).toEqual({ status: 'error' }))
  })

  it('reports a network failure as an error', async () => {
    const load = vi.fn().mockRejectedValue(new TypeError('offline'))
    const { result } = renderHook(() => useResource('key', load))

    await waitFor(() => expect(result.current).toEqual({ status: 'error' }))
  })

  it('goes back to loading for a new key instead of showing the old data', async () => {
    const load = vi.fn((signal: AbortSignal) => Promise.resolve(signal.aborted ? 'x' : 'value'))
    const { result, rerender } = renderHook(({ id }) => useResource(id, load), {
      initialProps: { id: 'one' },
    })
    await waitFor(() => expect(result.current.status).toBe('ready'))

    rerender({ id: 'two' })

    expect(result.current).toEqual({ status: 'loading' })
    await waitFor(() => expect(result.current.status).toBe('ready'))
  })

  it('cancels the request when it is no longer wanted, without reporting an error', async () => {
    let signalSeen: AbortSignal | undefined
    let rejectFirst: (reason: unknown) => void = () => {}
    const load = vi.fn((signal: AbortSignal) => {
      signalSeen ??= signal
      return signalSeen === signal
        ? new Promise<string>((_, reject) => {
            rejectFirst = reject
          })
        : Promise.resolve('second')
    })
    const { result, rerender } = renderHook(({ id }) => useResource(id, load), {
      initialProps: { id: 'one' },
    })

    rerender({ id: 'two' })
    expect(signalSeen?.aborted).toBe(true)
    rejectFirst(new DOMException('aborted', 'AbortError'))

    await waitFor(() => expect(result.current).toEqual({ status: 'ready', data: 'second' }))
  })

  it('aborts the request when the component goes away', () => {
    let signalSeen: AbortSignal | undefined
    const load = vi.fn((signal: AbortSignal) => {
      signalSeen = signal
      return new Promise<string>(() => {})
    })
    const { unmount } = renderHook(() => useResource('key', load))

    unmount()

    expect(signalSeen?.aborted).toBe(true)
  })
})
