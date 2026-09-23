import type { Profile } from '../content/profile'
import { FactsTable } from './FactsTable'
import { LinkRow } from './LinkRow'
import styles from './WelcomeHero.module.css'

interface WelcomeHeroProps {
  profile: Profile
}

/** Favicon size, in CSS pixels; the picture files are twice this so they stay sharp on retina. */
const INLINE_IMAGE_SIZE = 32

export function WelcomeHero({ profile }: WelcomeHeroProps) {
  const { headline } = profile

  return (
    <section className={styles.hero} aria-label="Introduction">
      <p className={styles.name}>{profile.name}</p>
      <p className={styles.tagline}>{profile.tagline}</p>
      <h1 className={styles.headline}>
        {headline.before}
        <span className={styles.highlight}>{headline.highlight}</span>
        {headline.after}
      </h1>
      <p className={styles.bio}>{profile.bio}</p>
      <div className={styles.facts}>
        <FactsTable facts={profile.facts} />
      </div>
      <div className={styles.links}>
        <LinkRow links={profile.links} align="center" />
      </div>
      <p className={styles.note}>
        {profile.askNote.map((part) =>
          typeof part === 'string' ? (
            part
          ) : (
            <img
              key={part.src}
              className={styles.inlineImage}
              src={part.src}
              alt={part.alt}
              width={INLINE_IMAGE_SIZE}
              height={INLINE_IMAGE_SIZE}
            />
          ),
        )}
      </p>
    </section>
  )
}
