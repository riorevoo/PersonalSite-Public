import { describe, expect, it } from 'vitest'
import { formatPostDate, formatReadTime } from './formatPost'

describe('formatPostDate', () => {
  it('spaces the parts of an ISO date the way the design does', () => {
    expect(formatPostDate('2026-08-14')).toBe('2026 · 08 · 14')
  })
})

describe('formatReadTime', () => {
  it('writes minutes', () => {
    expect(formatReadTime(9)).toBe('9 min')
    expect(formatReadTime(1)).toBe('1 min')
  })
})
