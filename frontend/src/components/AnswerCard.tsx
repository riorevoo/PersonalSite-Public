import { useRef } from 'react'
import type { MessageStatus } from '../hooks/useChat'
import utilities from '../styles/utilities.module.css'
import styles from './AnswerCard.module.css'

interface AnswerCardProps {
  status: MessageStatus
  text: string
  onRetry?: () => void
}

export function AnswerCard({ status, text, onRetry }: AnswerCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)

  // The retry button disappears once the retry starts, so park focus on the card instead of
  // letting it fall back to the page.
  function handleRetry() {
    onRetry?.()
    cardRef.current?.focus()
  }

  return (
    <div ref={cardRef} className={styles.card} tabIndex={-1}>
      <div className={styles.eyebrow}>◆ me</div>
      {status === 'pending' ? (
        <output className={styles.thinking}>
          <span className={utilities.srOnly}>thinking</span>
          <span aria-hidden="true" className={styles.dots}>
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        </output>
      ) : (
        <p className={styles.text}>{text}</p>
      )}
      {status === 'error' && (
        <button type="button" className={styles.retry} onClick={handleRetry}>
          try again
        </button>
      )}
    </div>
  )
}
