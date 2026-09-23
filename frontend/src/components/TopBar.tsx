import type { Ref } from 'react'
import { Link } from 'react-router'
import styles from './TopBar.module.css'

interface TopBarProps {
  name: string
  /** A conversation is under way, so show the name and "start over" on the left. */
  started: boolean
  /** Make the name the page heading. Off on pages that have a heading of their own. */
  nameAsHeading: boolean
  aboutOpen: boolean
  aboutButtonRef?: Ref<HTMLButtonElement>
  onReset: () => void
  onToggleAbout: () => void
  onOpenBlog: () => void
}

export function TopBar({
  name,
  started,
  nameAsHeading,
  aboutOpen,
  aboutButtonRef,
  onReset,
  onToggleAbout,
  onOpenBlog,
}: TopBarProps) {
  return (
    <header className={styles.bar}>
      <div className={styles.inner}>
        <div className={styles.left}>
          {started && (
            <>
              {nameAsHeading ? (
                <h1 className={styles.name}>{name}</h1>
              ) : (
                <p className={styles.name}>{name}</p>
              )}
              <button type="button" className={styles.reset} onClick={onReset}>
                start over
              </button>
            </>
          )}
        </div>
        <div className={styles.right}>
          <Link to="/writing" className={styles.pill} onClick={onOpenBlog}>
            ✎ blog
          </Link>
          <button
            ref={aboutButtonRef}
            type="button"
            className={styles.pill}
            aria-expanded={aboutOpen}
            aria-haspopup="dialog"
            onClick={onToggleAbout}
          >
            ◆ about me
          </button>
        </div>
      </div>
    </header>
  )
}
