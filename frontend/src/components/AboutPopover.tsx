import { useEffect, useRef, type RefObject } from 'react'
import type { Profile } from '../content/profile'
import styles from './AboutPopover.module.css'
import { FactsTable } from './FactsTable'
import { LinkRow } from './LinkRow'

interface AboutPopoverProps {
  profile: Profile
  /** The button that opens the popover; clicks on it are handled by the button itself. */
  triggerRef: RefObject<HTMLElement | null>
  /** restoreFocus is true when focus was inside the popover and should return to the trigger. */
  onClose: (restoreFocus: boolean) => void
}

export function AboutPopover({ profile, triggerRef, onClose }: AboutPopoverProps) {
  const rootRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    rootRef.current?.focus()
  }, [])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      onClose(rootRef.current?.contains(document.activeElement) ?? false)
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node
      if (rootRef.current?.contains(target) || triggerRef.current?.contains(target)) return
      onClose(false)
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('pointerdown', handlePointerDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [onClose, triggerRef])

  return (
    <dialog ref={rootRef} className={styles.popover} open aria-label="About me" tabIndex={-1}>
      <div className={styles.header}>
        <div>
          <div className={styles.name}>{profile.name}</div>
          <div className={styles.tagline}>{profile.shortTagline}</div>
        </div>
        <button
          type="button"
          className={styles.close}
          aria-label="Close"
          onClick={() => onClose(true)}
        >
          ✕
        </button>
      </div>
      <p className={styles.bio}>{profile.shortBio}</p>
      <div className={styles.facts}>
        <FactsTable facts={profile.facts} />
      </div>
      <div className={styles.links}>
        <LinkRow links={profile.links} align="start" />
      </div>
    </dialog>
  )
}
