import { useRef, type SyntheticEvent } from 'react'
import { MAX_MESSAGE_CHARS } from '../constants'
import styles from './Composer.module.css'

interface ComposerProps {
  /** The text in the box. The parent owns it so a suggested question can be put there. */
  value: string
  onChange: (text: string) => void
  onSubmit: (text: string) => void
  disabled?: boolean
  /** The box is being filled for the visitor (a chip was clicked); it cannot be edited meanwhile. */
  readOnly?: boolean
}

export function Composer({
  value,
  onChange,
  onSubmit,
  disabled = false,
  readOnly = false,
}: ComposerProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = value.trim()
    if (!text || disabled) return
    onSubmit(text)
    onChange('')
    inputRef.current?.focus()
  }

  return (
    <form className={styles.composer} onSubmit={handleSubmit}>
      <span className={styles.prompt} aria-hidden="true">
        &gt;
      </span>
      <input
        ref={inputRef}
        className={styles.input}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        readOnly={readOnly}
        placeholder="ask me something"
        aria-label="Ask me something"
        maxLength={MAX_MESSAGE_CHARS}
        autoComplete="off"
      />
      {/* aria-disabled (not `disabled`) so focus stays put while an answer is pending. */}
      <button type="submit" className={styles.send} aria-disabled={disabled}>
        SEND ⏎
      </button>
    </form>
  )
}
