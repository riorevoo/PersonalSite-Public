import type { ReactNode } from 'react'
import { BackLinks } from './BackLinks'
import styles from './PageNotice.module.css'

interface PageNoticeProps {
  /** The page heading, so a page that is only a message still has one. */
  heading: string
  /** Announce the message to assistive tech (for "loading"); errors and misses are plain text. */
  live?: boolean
  /** Also offer "all writing" (on a post page). */
  toWriting?: boolean
  children: ReactNode
}

/** A short message where a page would be (loading, failed, not found), with a way back. */
export function PageNotice({
  heading,
  live = false,
  toWriting = false,
  children,
}: PageNoticeProps) {
  return (
    <section className={styles.page} aria-label={heading}>
      <BackLinks toWriting={toWriting} />
      <h1 className={styles.heading}>{heading}</h1>
      {live ? (
        <output className={styles.notice}>{children}</output>
      ) : (
        <p className={styles.notice}>{children}</p>
      )}
    </section>
  )
}
