import type { ChatRequest, ChatResponse, HealthResponse, PostDetail, PostSummary } from './types'

/** Empty in dev (Vite proxies /api); set VITE_API_BASE_URL when the API lives elsewhere. */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: new Headers(init?.headers),
  })
  if (!response.ok) {
    throw new ApiError(
      response.status,
      `${init?.method ?? 'GET'} ${path} failed: ${response.status}`,
    )
  }
  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return request('/api/health')
}

export function postChat(body: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
  return request('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

export function getPosts(signal?: AbortSignal): Promise<PostSummary[]> {
  return request('/api/posts', { signal })
}

/** Rejects with an ApiError whose status is 404 when there is no post with this slug. */
export function getPost(slug: string, signal?: AbortSignal): Promise<PostDetail> {
  return request(`/api/posts/${encodeURIComponent(slug)}`, { signal })
}
