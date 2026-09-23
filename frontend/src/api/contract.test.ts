import { describe, expect, it } from 'vitest'
import openapi from '../../../backend/openapi.json'
import { MAX_HISTORY_TURN_CHARS } from '../constants'
import { MAX_HISTORY_TURNS } from '../hooks/useChat'

// The client's limits must never exceed what the backend contract accepts.
describe('backend contract limits', () => {
  const { ChatRequest, ChatTurn } = openapi.components.schemas

  it('keeps the history cap within the backend limit', () => {
    expect(MAX_HISTORY_TURNS).toBeLessThanOrEqual(ChatRequest.properties.history.maxItems)
  })

  it('keeps trimmed history turns within the backend limit', () => {
    expect(MAX_HISTORY_TURN_CHARS).toBeLessThanOrEqual(ChatTurn.properties.content.maxLength)
  })

  it('exposes the chat, health, posts and resume endpoints the site uses', () => {
    // /api/resume is not called by the client code: the resume link in profile.ts points at it.
    expect(Object.keys(openapi.paths).sort()).toEqual([
      '/api/chat',
      '/api/health',
      '/api/posts',
      '/api/posts/{slug}',
      '/api/resume',
    ])
  })
})
