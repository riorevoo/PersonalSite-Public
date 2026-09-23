import { Link } from 'react-router'
import type { PostSummary } from '../api/types'
import { formatPostDate, formatReadTime } from '../utils/formatPost'
import { BackLinks } from './BackLinks'
import styles from './WritingList.module.css'

interface WritingListProps {
  heading: string
  intro: string
  posts: PostSummary[]
}

export function WritingList({ heading, intro, posts }: WritingListProps) {
  return (
    <section className={styles.page} aria-label={heading}>
      <BackLinks />
      <h1 className={styles.heading}>{heading}</h1>
      <p className={styles.intro}>{intro}</p>
      {posts.length === 0 ? (
        <p className={styles.empty}>Nothing published yet.</p>
      ) : (
        <ul className={styles.list}>
          {posts.map((post) => (
            <li key={post.slug} className={styles.item}>
              <div>
                <h2 className={styles.title}>
                  {/* The link's ::after covers the whole row, so the row is one click target. */}
                  <Link to={`/writing/${post.slug}`} className={styles.link}>
                    {post.title}
                  </Link>
                </h2>
                <p className={styles.dek}>{post.dek}</p>
                <p className={styles.tag}>
                  {post.draft && 'draft · '}
                  {post.tag}
                </p>
              </div>
              <p className={styles.when}>
                <time dateTime={post.date}>{formatPostDate(post.date)}</time>
                <span>{formatReadTime(post.read_minutes)}</span>
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
