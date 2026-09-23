import type { ProfileLink } from '../content/profile'
import styles from './LinkRow.module.css'

interface LinkRowProps {
  links: ProfileLink[]
  align?: 'center' | 'start'
}

function isExternal(href: string): boolean {
  return /^https?:\/\//.test(href)
}

export function LinkRow({ links, align = 'center' }: LinkRowProps) {
  return (
    <ul className={`${styles.list} ${align === 'center' ? styles.center : styles.start}`}>
      {links.map((link) => (
        <li key={link.label}>
          <a
            className={styles.link}
            href={link.href}
            {...(link.newTab || isExternal(link.href)
              ? { target: '_blank', rel: 'noopener noreferrer' }
              : {})}
          >
            → {link.label}
          </a>
        </li>
      ))}
    </ul>
  )
}
