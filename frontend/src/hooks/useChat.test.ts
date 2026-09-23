import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MAX_HISTORY_TURN_CHARS, REQUEST_TIMEOUT_MS } from '../constants'
import { ERROR_TEXT, MAX_HISTORY_TURNS, RATE_LIMIT_TEXT, useChat } from './useChat'

function answerWith(text: string) {
  return new Response(JSON.stringify({ answer: text }), { status: 200 })
}

function bodyOf(fetchMock: ReturnType<typeof vi.fn>, call: number) {
  const init = fetchMock.mock.calls[call]?.[1] as RequestInit
  return JSON.parse(init.body as string) as {
    message: string
    history: { role: string; content: string }[]
  }
}

describe('useChat', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('starts empty', () => {
    const { result } = renderHook(() => useChat())
    expect(result.current.messages).toEqual([])
    expect(result.current.pending).toBe(false)
  })

  it('adds a pending message, then fills in the answer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(answerWith('hello back')))
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('  hello  '))

    expect(result.current.messages).toMatchObject([{ question: 'hello', status: 'pending' }])
    expect(result.current.pending).toBe(true)

    await waitFor(() => expect(result.current.pending).toBe(false))
    expect(result.current.messages).toMatchObject([
      { question: 'hello', answer: 'hello back', status: 'done' },
    ])
  })

  it('ignores blank questions', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('   '))

    expect(result.current.messages).toEqual([])
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('ignores a new question while one is in flight', () => {
    const fetchMock = vi.fn().mockReturnValue(new Promise(() => {}))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('first'))
    act(() => result.current.ask('second'))

    expect(result.current.messages).toHaveLength(1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('sends earlier finished exchanges as history', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(answerWith('one'))
      .mockResolvedValueOnce(answerWith('two'))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('q1'))
    await waitFor(() => expect(result.current.pending).toBe(false))
    act(() => result.current.ask('q2'))
    await waitFor(() => expect(result.current.pending).toBe(false))

    expect(bodyOf(fetchMock, 0).history).toEqual([])
    expect(bodyOf(fetchMock, 1)).toEqual({
      message: 'q2',
      history: [
        { role: 'user', content: 'q1' },
        { role: 'assistant', content: 'one' },
      ],
    })
  })

  it('caps the history it sends', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(answerWith('a')))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    const questions = MAX_HISTORY_TURNS + 3
    for (let i = 0; i < questions; i++) {
      act(() => result.current.ask(`q${i}`))
      await waitFor(() => expect(result.current.pending).toBe(false))
    }

    expect(bodyOf(fetchMock, questions - 1).history).toHaveLength(MAX_HISTORY_TURNS)
  })

  it('trims a very long answer before sending it back as history', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(answerWith('x'.repeat(MAX_HISTORY_TURN_CHARS + 500)))
      .mockResolvedValueOnce(answerWith('ok'))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('q1'))
    await waitFor(() => expect(result.current.pending).toBe(false))
    act(() => result.current.ask('q2'))
    await waitFor(() => expect(result.current.pending).toBe(false))

    expect(bodyOf(fetchMock, 1).history[1]?.content).toHaveLength(MAX_HISTORY_TURN_CHARS)
    // The full answer is still what the visitor sees.
    expect(result.current.messages[0]?.answer).toHaveLength(MAX_HISTORY_TURN_CHARS + 500)
  })

  it('fails with an error card when the backend never answers in time', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () =>
              reject(new DOMException('aborted', 'AbortError')),
            )
          }),
      ),
    )
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('hello?'))
    expect(result.current.pending).toBe(true)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS)
    })

    expect(result.current.messages).toMatchObject([{ status: 'error', answer: ERROR_TEXT }])
    expect(result.current.pending).toBe(false)
  })

  it('does not time out an answer that arrived in time, and leaves no timer behind', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(answerWith('quick')))
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('hi'))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(vi.getTimerCount()).toBe(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS * 2)
    })

    expect(result.current.messages).toMatchObject([{ status: 'done', answer: 'quick' }])
  })

  it('marks the message as failed on a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('hi'))
    await waitFor(() => expect(result.current.pending).toBe(false))

    expect(result.current.messages).toMatchObject([{ status: 'error', answer: ERROR_TEXT }])
  })

  it('marks the message as failed on a non-2xx response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 500 })))
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('hi'))
    await waitFor(() => expect(result.current.pending).toBe(false))

    expect(result.current.messages).toMatchObject([{ status: 'error', answer: ERROR_TEXT }])
  })

  it('shows a specific message, and allows a retry, when the server rate-limits the visitor', async () => {
    const detail = JSON.stringify({ detail: 'Too many questions.' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(detail, { status: 429 }))
      .mockResolvedValueOnce(answerWith('fine now'))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('hi'))
    await waitFor(() => expect(result.current.pending).toBe(false))
    expect(result.current.messages).toMatchObject([{ status: 'error', answer: RATE_LIMIT_TEXT }])

    act(() => result.current.retry(result.current.messages[0]?.id ?? -1))
    await waitFor(() => expect(result.current.pending).toBe(false))
    expect(result.current.messages).toMatchObject([{ status: 'done', answer: 'fine now' }])
  })

  it('retries a failed question with the history before it', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(answerWith('fine'))
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(answerWith('recovered'))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('q1'))
    await waitFor(() => expect(result.current.pending).toBe(false))
    act(() => result.current.ask('q2'))
    await waitFor(() => expect(result.current.messages[1]?.status).toBe('error'))

    act(() => result.current.retry(result.current.messages[1]?.id ?? -1))
    expect(result.current.messages[1]).toMatchObject({ status: 'pending', answer: '' })
    await waitFor(() => expect(result.current.pending).toBe(false))

    expect(result.current.messages[1]).toMatchObject({ answer: 'recovered', status: 'done' })
    expect(bodyOf(fetchMock, 2)).toEqual({
      message: 'q2',
      history: [
        { role: 'user', content: 'q1' },
        { role: 'assistant', content: 'fine' },
      ],
    })
  })

  it('ignores retry for unknown, finished or in-flight messages', async () => {
    const fetchMock = vi.fn().mockResolvedValue(answerWith('ok'))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('q1'))
    await waitFor(() => expect(result.current.pending).toBe(false))
    const id = result.current.messages[0]?.id ?? -1

    act(() => result.current.retry(id)) // finished
    act(() => result.current.retry(999)) // unknown

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not retry while another question is in flight', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('offline'))
      .mockReturnValueOnce(new Promise(() => {}))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('q1'))
    await waitFor(() => expect(result.current.messages[0]?.status).toBe('error'))
    const failedId = result.current.messages[0]?.id ?? -1
    act(() => result.current.retry(failedId)) // now pending
    act(() => result.current.retry(failedId)) // ignored, already pending

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('reset clears the conversation and cancels the request in flight', async () => {
    let signal: AbortSignal | undefined
    let resolve: (value: Response) => void = () => {}
    const fetchMock = vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      signal = init.signal ?? undefined
      return new Promise<Response>((r) => {
        resolve = r
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('slow one'))
    act(() => result.current.reset())

    expect(result.current.messages).toEqual([])
    expect(signal?.aborted).toBe(true)

    // A late response for the cancelled question must not bring it back.
    await act(async () => resolve(answerWith('too late')))
    expect(result.current.messages).toEqual([])
  })

  it('reset with nothing in flight is harmless', () => {
    const { result } = renderHook(() => useChat())
    act(() => result.current.reset())
    expect(result.current.messages).toEqual([])
  })

  it('cancels the request in flight when unmounted', () => {
    let signal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, init: RequestInit) => {
        signal = init.signal ?? undefined
        return new Promise(() => {})
      }),
    )
    const { result, unmount } = renderHook(() => useChat())

    act(() => result.current.ask('hi'))
    unmount()

    expect(signal?.aborted).toBe(true)
  })

  it('does not report a failure for a request that was cancelled', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, init: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => reject(new DOMException('x', 'AbortError')))
        })
      }),
    )
    const { result } = renderHook(() => useChat())

    act(() => result.current.ask('hi'))
    await act(async () => result.current.reset())

    expect(result.current.messages).toEqual([])
  })
})
