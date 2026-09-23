import { useCallback, useEffect, useRef, useState } from 'react'
import { AUTOFILL_DELAY_MS } from '../constants'

interface Autofill {
  /** What is in the text box. */
  draft: string
  setDraft: (text: string) => void
  /** A suggested question is in the box and about to be sent; the box should not be edited. */
  filling: boolean
  /** Put `text` in the box, hold it for a beat so it can be seen, then send it and clear the box. */
  autofill: (text: string) => void
  /** Drop a pending autofill and empty the box (start over). */
  cancel: () => void
}

/** The text box's contents plus "auto fill": what the suggestion chips do when they are clicked. */
export function useAutofill(send: (text: string) => void): Autofill {
  const [draft, setDraft] = useState('')
  const [filling, setFilling] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  // The newest `send`, so a pending autofill never fires a stale one.
  const latestSend = useRef(send)
  useEffect(() => {
    latestSend.current = send
  })

  const cancel = useCallback(() => {
    clearTimeout(timer.current)
    timer.current = undefined
    setFilling(false)
    setDraft('')
  }, [])

  const autofill = useCallback((text: string) => {
    if (timer.current !== undefined) return // one at a time
    setDraft(text)
    setFilling(true)
    timer.current = setTimeout(() => {
      timer.current = undefined
      setFilling(false)
      setDraft('')
      latestSend.current(text)
    }, AUTOFILL_DELAY_MS)
  }, [])

  useEffect(() => () => clearTimeout(timer.current), [])

  return { draft, setDraft, filling, autofill, cancel }
}
