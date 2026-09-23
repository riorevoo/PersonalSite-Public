import { useParams } from 'react-router'
import { PageNotice } from '../components/PageNotice'
import { PostView } from '../components/PostView'
import { usePost } from '../hooks/usePosts'

interface PostRouteProps {
  /** The section's heading, for the pages that are only a message. */
  heading: string
  /** Questions offered under the post. */
  questions: string[]
  onAsk: (question: string) => void
}

/** /writing/:slug: one post. */
export function PostRoute({ heading, questions, onAsk }: PostRouteProps) {
  const { slug = '' } = useParams()
  const post = usePost(slug)

  switch (post.status) {
    case 'ready':
      return <PostView post={post.data} questions={questions} onAsk={onAsk} />
    case 'loading':
      return (
        <PageNotice heading={heading} live toWriting>
          loading…
        </PageNotice>
      )
    case 'not-found':
      return (
        <PageNotice heading="NOT FOUND" toWriting>
          There is no post at this address.
        </PageNotice>
      )
    default:
      return (
        <PageNotice heading={heading} toWriting>
          I could not load this post just now. Please try again in a moment.
        </PageNotice>
      )
  }
}
