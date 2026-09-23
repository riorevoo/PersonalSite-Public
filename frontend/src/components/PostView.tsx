import type { PostDetail } from '../api/types'
import { formatPostDate, formatReadTime } from '../utils/formatPost'
import { BackLinks } from './BackLinks'
import { PostBody } from './PostBody'
import styles from './PostView.module.css'

interface PostViewProps {
  post: PostDetail
  /** Questions offered under the post ("ask about this"). */
  questions: string[]
  onAsk: (question: string) => void
}

export function PostView({ post, questions, onAsk }: PostViewProps) {
  return (
    <article className={styles.page}>
      <BackLinks toWriting />
      <header>
        <p className={styles.meta}>
          {post.draft && 'draft · '}
          {post.tag} · <time dateTime={post.date}>{formatPostDate(post.date)}</time> ·{' '}
          {formatReadTime(post.read_minutes)}
        </p>
        <h1 className={styles.title}>{post.title}</h1>
        <p className={styles.dek}>{post.dek}</p>
        <div className={styles.rule} aria-hidden="true" />
      </header>
      <PostBody markdown={post.body} />
      <aside className={styles.ask} aria-label="Ask about this post">
        <p className={styles.askLabel}>ask about this</p>
        <div className={styles.chips}>
          {questions.map((question) => (
            <button
              key={question}
              type="button"
              className={styles.chip}
              onClick={() => onAsk(question)}
            >
              {question}
            </button>
          ))}
        </div>
      </aside>
    </article>
  )
}
