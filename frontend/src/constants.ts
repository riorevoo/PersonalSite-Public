/** Longest question the backend accepts (keep in sync with APP_MAX_MESSAGE_CHARS). */
export const MAX_MESSAGE_CHARS = 500

/** Longest history turn the backend accepts (MAX_TURN_CHARS in backend/app/schemas/chat.py). */
export const MAX_HISTORY_TURN_CHARS = 4000

/** How long to wait for an API response before showing an error. */
export const REQUEST_TIMEOUT_MS = 30_000

/** How long a suggested question stays in the text box before it is sent, so it can be seen. */
export const AUTOFILL_DELAY_MS = 350
