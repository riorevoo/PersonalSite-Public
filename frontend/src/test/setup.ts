import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

beforeEach(() => {
  // jsdom does not implement scrollIntoView; the message list calls it.
  Element.prototype.scrollIntoView = vi.fn()
})

afterEach(() => cleanup())
