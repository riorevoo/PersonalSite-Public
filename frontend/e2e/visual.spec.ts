import { expect, test } from '@playwright/test'
import { aboutButton, ask, fontsReady, POSTS } from './helpers'

// Screenshot baselines guard the design. They are made on the developer's machine and only run
// locally (see grepInvert in playwright.config.ts). After an intended visual change, review the
// diff against the design screenshot (kept offline) and run `npm run e2e:update`.

test('welcome screen looks like the design @visual', async ({ page }) => {
  await page.goto('/')
  await fontsReady(page)
  await expect(page).toHaveScreenshot('welcome.png')
})

test('conversation looks like the design @visual', async ({ page }) => {
  await page.goto('/')
  await ask(page, 'what experience do you have?')
  await fontsReady(page)
  await page.mouse.move(0, 0) // no hover highlight in the picture
  await expect(page).toHaveScreenshot('conversation.png')
})

test('writing list looks like the design @visual', async ({ page }) => {
  await page.goto('/writing')
  await page.getByRole('heading', { level: 1, name: 'WRITING' }).waitFor()
  await fontsReady(page)
  await page.mouse.move(0, 0)
  await expect(page).toHaveScreenshot('writing.png')
})

test('post looks like the design @visual', async ({ page }) => {
  await page.goto(`/writing/${POSTS.newest.slug}`)
  await page.getByRole('heading', { level: 1, name: POSTS.newest.title }).waitFor()
  await fontsReady(page)
  await page.mouse.move(0, 0)
  await expect(page).toHaveScreenshot('post.png')
})

test('about popover looks like the design @visual', async ({ page }) => {
  await page.goto('/')
  await ask(page, 'what experience do you have?')
  await aboutButton(page).click()
  await fontsReady(page)
  await page.mouse.move(0, 0)
  await expect(page).toHaveScreenshot('about-popover.png')
})
