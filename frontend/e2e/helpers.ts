import { expect, type Locator, type Page } from '@playwright/test'

/** The suggestion chips, in page order (must match src/content/profile.ts). */
export const CHIPS = [
  'what experience do you have?',
  'what projects have you worked on?',
  'what are you interested in right now?',
] as const

export const chip = (page: Page, text: string): Locator => page.getByRole('button', { name: text })
export const composer = (page: Page): Locator =>
  page.getByRole('textbox', { name: 'Ask me something' })
export const conversation = (page: Page): Locator => page.getByRole('log', { name: 'Conversation' })
export const aboutButton = (page: Page): Locator => page.getByRole('button', { name: '◆ about me' })
export const aboutDialog = (page: Page): Locator => page.getByRole('dialog', { name: 'About me' })
export const blogLink = (page: Page): Locator => page.getByRole('link', { name: '✎ blog' })
export const startOver = (page: Page): Locator => page.getByRole('button', { name: 'start over' })
export const githubLink = (page: Page): Locator => page.getByRole('link', { name: '→ github' })
export const resumeLink = (page: Page): Locator =>
  page.getByRole('link', { name: '→ résumé (pdf)' })

/** The made-up posts in e2e/fixtures/knowledge/posts (the test backend reads that folder). */
export const POSTS = {
  newest: { slug: 'sample-retries', title: 'A sample post about retries' },
  oldest: { slug: 'sample-chunking', title: 'A sample post about chunking' },
  draft: { slug: 'hidden-draft', title: 'A draft that stays hidden' },
} as const

/** Wait for the web fonts, so text has its final metrics before measuring or screenshotting. */
export async function fontsReady(page: Page): Promise<void> {
  await page.evaluate(() => document.fonts.ready)
}

/** Ask by typing and pressing Enter, then wait until the answer has replaced "thinking". */
export async function ask(page: Page, question: string): Promise<void> {
  await composer(page).fill(question)
  await composer(page).press('Enter')
  await expectAnswered(page)
}

/**
 * A question was sent and no question is pending, and the newest answer card has real text (not
 * an error). Waits for the conversation first: a chip sends a beat after it is clicked, so "no
 * question pending" alone would be true before anything has been asked.
 */
export async function expectAnswered(page: Page): Promise<void> {
  await expect(conversation(page)).toBeVisible()
  await expect(page.getByRole('status')).toHaveCount(0)
  await expect(conversation(page)).not.toContainText('could not reach my answering service')
  await expect(conversation(page).getByText('◆ me').last()).toBeVisible()
}

/** True if the page scrolls sideways. */
export async function hasHorizontalScroll(page: Page): Promise<boolean> {
  return page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
}
