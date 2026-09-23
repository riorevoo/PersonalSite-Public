import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getHealth, getPost, getPosts, postChat } from './client'

function stubFetch(response: Response) {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

describe('api client', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('getHealth returns the parsed body', async () => {
    const fetchMock = stubFetch(jsonResponse({ status: 'ok' }))
    await expect(getHealth()).resolves.toEqual({ status: 'ok' })
    expect(fetchMock).toHaveBeenCalledWith('/api/health', expect.any(Object))
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).has('Content-Type')).toBe(false)
  })

  it('postChat sends a JSON body and returns the answer', async () => {
    const fetchMock = stubFetch(jsonResponse({ answer: 'hello' }))
    const body = { message: 'hi', history: [{ role: 'user' as const, content: 'earlier' }] }

    await expect(postChat(body)).resolves.toEqual({ answer: 'hello' })

    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('/api/chat')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe(JSON.stringify(body))
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
  })

  it('postChat passes the abort signal through to fetch', async () => {
    const fetchMock = stubFetch(jsonResponse({ answer: 'hello' }))
    const controller = new AbortController()

    await postChat({ message: 'hi', history: [] }, controller.signal)

    const [, init] = fetchMock.mock.calls[0] ?? []
    expect(init?.signal).toBe(controller.signal)
  })

  it('does not send a JSON content type for bodyless post reads', async () => {
    const fetchMock = stubFetch(jsonResponse([]))
    await getPosts()
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).has('Content-Type')).toBe(false)
  })

  it('throws ApiError carrying the status on a non-2xx response', async () => {
    stubFetch(jsonResponse({ detail: 'nope' }, 422))

    const error = await postChat({ message: '', history: [] }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(422)
    expect((error as ApiError).message).toContain('POST /api/chat')
  })

  it('names the method as GET for failed reads', async () => {
    stubFetch(jsonResponse({}, 500))
    await expect(getHealth()).rejects.toThrow('GET /api/health failed: 500')
  })

  it('getPosts returns the list and passes the abort signal through', async () => {
    const posts = [{ slug: 'a', title: 'A' }]
    const fetchMock = stubFetch(jsonResponse(posts))
    const controller = new AbortController()

    await expect(getPosts(controller.signal)).resolves.toEqual(posts)

    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('/api/posts')
    expect(init?.signal).toBe(controller.signal)
  })

  it('getPost asks for one post by slug, encoding it', async () => {
    const fetchMock = stubFetch(jsonResponse({ slug: 'a b', body: 'text' }))

    await expect(getPost('a b')).resolves.toEqual({ slug: 'a b', body: 'text' })

    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/posts/a%20b')
  })

  it('getPost rejects with a 404 ApiError for an unknown slug', async () => {
    stubFetch(jsonResponse({ detail: 'Post not found.' }, 404))

    const error = await getPost('nope').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })
})
