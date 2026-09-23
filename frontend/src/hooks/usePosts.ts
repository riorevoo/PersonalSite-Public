import { useCallback } from 'react'
import { getPost, getPosts } from '../api/client'
import type { PostDetail, PostSummary } from '../api/types'
import { useResource, type Resource } from './useResource'

/** Every published post, newest first. */
export function usePosts(): Resource<PostSummary[]> {
  return useResource('posts', getPosts)
}

/** One post by slug. Status "not-found" means there is no such post. */
export function usePost(slug: string): Resource<PostDetail> {
  const load = useCallback((signal: AbortSignal) => getPost(slug, signal), [slug])
  return useResource(slug, load)
}
