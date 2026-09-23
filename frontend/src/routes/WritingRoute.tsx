import { PageNotice } from '../components/PageNotice'
import { WritingList } from '../components/WritingList'
import { usePosts } from '../hooks/usePosts'

interface WritingRouteProps {
  heading: string
  intro: string
}

/** /writing: every published post. */
export function WritingRoute({ heading, intro }: WritingRouteProps) {
  const posts = usePosts()

  switch (posts.status) {
    case 'ready':
      return <WritingList heading={heading} intro={intro} posts={posts.data} />
    case 'loading':
      return (
        <PageNotice heading={heading} live>
          loading…
        </PageNotice>
      )
    default:
      return (
        <PageNotice heading={heading}>
          I could not load the writing just now. Please try again in a moment.
        </PageNotice>
      )
  }
}
