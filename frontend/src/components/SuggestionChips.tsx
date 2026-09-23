import utilities from '../styles/utilities.module.css'
import styles from './SuggestionChips.module.css'

interface SuggestionChipsProps {
  suggestions: string[]
  disabled?: boolean
  onPick: (question: string) => void
}

/**
 * While disabled the chips use aria-disabled rather than `disabled`, so a keyboard user who just
 * pressed one keeps their place instead of focus dropping to the page.
 */
export function SuggestionChips({ suggestions, disabled = false, onPick }: SuggestionChipsProps) {
  return (
    <fieldset className={styles.chips}>
      <legend className={utilities.srOnly}>Suggested questions</legend>
      {suggestions.map((question) => (
        <button
          key={question}
          type="button"
          className={styles.chip}
          aria-disabled={disabled}
          onClick={() => {
            if (!disabled) onPick(question)
          }}
        >
          {question}
        </button>
      ))}
    </fieldset>
  )
}
