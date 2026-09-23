import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, postChat } from '../api/client'
import type { ChatTurn } from '../api/types'
import { MAX_HISTORY_TURN_CHARS, REQUEST_TIMEOUT_MS } from '../constants'

export type MessageStatus = 'pending' | 'done' | 'error'

export interface Message {
  id: number
  question: string
  answer: string
  status: MessageStatus
}

/** How many earlier turns (user + assistant messages) are sent along with each question. */
export const MAX_HISTORY_TURNS = 10

/** Shown in the answer card when the request fails. */
export const ERROR_TEXT =
  'I could not reach my answering service just now. Please try again in a moment.'

/** Shown when the server says this visitor has asked too many questions (HTTP 429). */
export const RATE_LIMIT_TEXT =
  "You're asking faster than I can answer. Give me a minute and try again."

function errorText(error: unknown): string {
  return error instanceof ApiError && error.status === 429 ? RATE_LIMIT_TEXT : ERROR_TEXT
}

function buildHistory(messages: Message[]): ChatTurn[] {
  const turns = messages
    .filter((message) => message.status === 'done')
    .flatMap((message): ChatTurn[] => [
      { role: 'user', content: message.question },
      // The backend rejects turns over its limit, so a very long answer is trimmed here.
      { role: 'assistant', content: message.answer.slice(0, MAX_HISTORY_TURN_CHARS) },
    ])
  return turns.slice(-MAX_HISTORY_TURNS)
}

/**
 * Conversation state: one question in flight at a time, a reset that cancels it,
 * a timeout so a hung backend surfaces as an error, and retry for failed questions.
 */
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  // The ref is the source of truth so callbacks never read stale state.
  const messagesRef = useRef<Message[]>([])
  const nextId = useRef(1)
  const controller = useRef<AbortController | null>(null)

  const commit = useCallback((next: Message[]) => {
    messagesRef.current = next
    setMessages(next)
  }, [])

  const send = useCallback(
    async (id: number, question: string, history: ChatTurn[]) => {
      const current = new AbortController()
      controller.current = current
      let timedOut = false
      const timer = setTimeout(() => {
        timedOut = true
        current.abort()
      }, REQUEST_TIMEOUT_MS)
      const settle = (patch: Partial<Message>) =>
        commit(messagesRef.current.map((m) => (m.id === id ? { ...m, ...patch } : m)))

      try {
        const { answer } = await postChat({ message: question, history }, current.signal)
        if (!current.signal.aborted) settle({ answer, status: 'done' })
      } catch (error) {
        // A reset or unmount aborts on purpose and needs no error card; a timeout does.
        if (!current.signal.aborted || timedOut) {
          settle({ answer: errorText(error), status: 'error' })
        }
      } finally {
        clearTimeout(timer)
      }
    },
    [commit],
  )

  const ask = useCallback(
    (raw: string) => {
      const question = raw.trim()
      const list = messagesRef.current
      if (!question || list.some((m) => m.status === 'pending')) return

      const id = nextId.current++
      commit([...list, { id, question, answer: '', status: 'pending' }])
      void send(id, question, buildHistory(list))
    },
    [commit, send],
  )

  const retry = useCallback(
    (id: number) => {
      const list = messagesRef.current
      const target = list.find((m) => m.id === id)
      if (target?.status !== 'error' || list.some((m) => m.status === 'pending')) return

      commit(list.map((m) => (m.id === id ? { ...m, answer: '', status: 'pending' } : m)))
      void send(id, target.question, buildHistory(list.filter((m) => m.id < id)))
    },
    [commit, send],
  )

  const reset = useCallback(() => {
    controller.current?.abort()
    controller.current = null
    commit([])
  }, [commit])

  useEffect(() => () => controller.current?.abort(), [])

  const pending = messages.some((m) => m.status === 'pending')

  return { messages, pending, ask, retry, reset }
}
