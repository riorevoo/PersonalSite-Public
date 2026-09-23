/** "2026-08-14" becomes "2026 · 08 · 14", the way the design writes a post date. */
export function formatPostDate(isoDate: string): string {
  return isoDate.split('-').join(' · ')
}

/** 9 becomes "9 min". */
export function formatReadTime(minutes: number): string {
  return `${minutes} min`
}
