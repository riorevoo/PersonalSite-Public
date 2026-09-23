import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AUTOFILL_DELAY_MS } from '../constants'
import { useAutofill } from './useAutofill'

describe('useAutofill', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('starts with an empty box', () => {
    const { result } = renderHook(() => useAutofill(vi.fn()))

    expect(result.current.draft).toBe('')
    expect(result.current.filling).toBe(false)
  })

  it('puts the text in the box straight away but does not send it yet', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('what do you do?'))

    expect(result.current.draft).toBe('what do you do?')
    expect(result.current.filling).toBe(true)
    expect(send).not.toHaveBeenCalled()
  })

  it('sends it after the delay and empties the box', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('what do you do?'))
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS))

    expect(send).toHaveBeenCalledExactlyOnceWith('what do you do?')
    expect(result.current.draft).toBe('')
    expect(result.current.filling).toBe(false)
  })

  it('waits the whole delay before sending', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('question'))
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS - 1))

    expect(send).not.toHaveBeenCalled()
  })

  it('ignores a second autofill while one is under way', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('first'))
    act(() => result.current.autofill('second'))
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS))

    expect(send).toHaveBeenCalledExactlyOnceWith('first')
  })

  it('can autofill again once the first one has been sent', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('first'))
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS))
    act(() => result.current.autofill('second'))
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS))

    expect(send).toHaveBeenNthCalledWith(1, 'first')
    expect(send).toHaveBeenNthCalledWith(2, 'second')
  })

  it('cancel drops the pending send and empties the box', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('question'))
    act(() => result.current.cancel())
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS * 2))

    expect(send).not.toHaveBeenCalled()
    expect(result.current.draft).toBe('')
    expect(result.current.filling).toBe(false)
  })

  it('sends with the newest send function, not the one from when it started', () => {
    const first = vi.fn()
    const second = vi.fn()
    const { result, rerender } = renderHook(({ send }) => useAutofill(send), {
      initialProps: { send: first },
    })

    act(() => result.current.autofill('question'))
    rerender({ send: second })
    act(() => vi.advanceTimersByTime(AUTOFILL_DELAY_MS))

    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledExactlyOnceWith('question')
  })

  it('does not send after it is unmounted', () => {
    const send = vi.fn()
    const { result, unmount } = renderHook(() => useAutofill(send))

    act(() => result.current.autofill('question'))
    unmount()
    vi.advanceTimersByTime(AUTOFILL_DELAY_MS * 2)

    expect(send).not.toHaveBeenCalled()
  })

  it('lets the visitor type into the box when nothing is being filled', () => {
    const { result } = renderHook(() => useAutofill(vi.fn()))

    act(() => result.current.setDraft('typed'))

    expect(result.current.draft).toBe('typed')
  })
})
