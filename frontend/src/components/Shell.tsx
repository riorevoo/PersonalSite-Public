import type { ReactNode } from 'react'
import styles from './Shell.module.css'

interface ShellProps {
  /** Rendered above the scroll area. */
  topBar?: ReactNode
  /** Absolutely positioned layer over the shell (the about-me popover). */
  overlay?: ReactNode
  /** Pinned below the scroll area (chips and composer). Left out on pages that are just text. */
  footer?: ReactNode
  /** "chat" is the conversation; "reading" is a page of text with the design's reading padding. */
  layout?: 'chat' | 'reading'
  children: ReactNode
}

/**
 * The page is as wide as the window, so the scrollbar sits at the window's edge. The design's
 * 1100px column is centred inside each band (top bar, scroll area, footer) instead.
 */
export function Shell({ topBar, overlay, footer, layout = 'chat', children }: ShellProps) {
  return (
    <div className={styles.shell}>
      {topBar}
      {overlay && <div className={styles.overlay}>{overlay}</div>}
      <main className={styles.scroll} data-layout={layout}>
        <div className={styles.column}>{children}</div>
      </main>
      {footer && (
        <footer className={styles.footer}>
          <div className={styles.column}>{footer}</div>
        </footer>
      )}
    </div>
  )
}
