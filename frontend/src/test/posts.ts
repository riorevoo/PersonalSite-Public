import type { PostDetail, PostSummary } from '../api/types'

/** Made-up posts for tests. */
export function summary(overrides: Partial<PostSummary> = {}): PostSummary {
  return {
    slug: 'a-post',
    title: 'A post title',
    dek: 'One sentence about the post.',
    tag: 'notes',
    date: '2026-08-14',
    read_minutes: 9,
    draft: false,
    ...overrides,
  }
}

export function detail(overrides: Partial<PostDetail> = {}): PostDetail {
  return {
    ...summary(),
    body: 'First paragraph.\n\n## A section\nMore text.',
    ...overrides,
  }
}

/** A fetch stub that answers by URL: `{ '/api/posts': [...], '/api/posts/a-post': {...} }`. */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = (input: RequestInfo | URL) => {
    const path = String(input)
    return path in routes
      ? Promise.resolve(new Response(JSON.stringify(routes[path]), { status: 200 }))
      : Promise.resolve(
          new Response(JSON.stringify({ detail: 'Post not found.' }), { status: 404 }),
        )
  }
  return fetchMock
}
