import { Link } from 'react-router'
import styles from './BackLinks.module.css'

interface BackLinksProps {
  /** Also offer "all writing" (on a post page). */
  toWriting?: boolean
}

export function BackLinks({ toWriting = false }: BackLinksProps) {
  return (
    <nav className={styles.links} aria-label="Back">
      {toWriting && (
        <Link to="/writing" className={styles.link}>
          ← all writing
        </Link>
      )}
      <Link to="/" className={styles.link}>
        ← back to asking
      </Link>
    </nav>
  )
}
