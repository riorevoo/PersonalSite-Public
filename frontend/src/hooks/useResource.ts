import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { REQUEST_TIMEOUT_MS } from '../constants'

export type Resource<T> =
  | { status: 'loading' }
  | { status: 'ready'; data: T }
  | { status: 'not-found' }
  | { status: 'error' }

interface Settled<T> {
  key: string
  resource: Exclude<Resource<T>, { status: 'loading' }>
}

/**
 * Loads one thing from the API. `key` says what is being loaded (a new key starts a new load and
 * cancels the old one); `load` must be stable for a given key. A 404 is reported as "not-found"
 * rather than "error", so a page can tell a missing post from a broken connection.
 */
export function useResource<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
): Resource<T> {
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => {
      controller.abort()
      setSettled({ key, resource: { status: 'error' } })
    }, REQUEST_TIMEOUT_MS)
    load(controller.signal)
      .then((data) =>
        controller.signal.aborted
          ? undefined
          : setSettled({ key, resource: { status: 'ready', data } }),
      )
      .catch((error: unknown) => {
        // Leaving the page or asking for something else aborts on purpose; that is not an error.
        if (controller.signal.aborted) return
        const missing = error instanceof ApiError && error.status === 404
        setSettled({ key, resource: { status: missing ? 'not-found' : 'error' } })
      })
      .finally(() => clearTimeout(timer))
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [key, load])

  // Anything settled for a different key is stale, which is the same as still loading.
  return settled?.key === key ? settled.resource : { status: 'loading' }
}
