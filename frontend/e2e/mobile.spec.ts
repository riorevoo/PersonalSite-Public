import { expect, test } from '@playwright/test'
import {
  aboutButton,
  aboutDialog,
  blogLink,
  CHIPS,
  chip,
  composer,
  conversation,
  expectAnswered,
  fontsReady,
  hasHorizontalScroll,
  POSTS,
} from './helpers'

// Runs in the "mobile" project (a Pixel 7 with touch).

test('the whole flow works by tapping, without sideways scrolling', async ({ page }) => {
  await page.goto('/')
  await fontsReady(page)
  expect(await hasHorizontalScroll(page)).toBe(false)

  await chip(page, CHIPS[0]).tap()
  await expectAnswered(page)
  await expect(conversation(page)).toContainText(CHIPS[0])

  await aboutButton(page).tap()
  await expect(aboutDialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).tap()
  await expect(aboutDialog(page)).toHaveCount(0)

  await page.getByRole('button', { name: 'start over' }).tap()
  await expect(page.getByRole('button', { name: 'start over' })).toHaveCount(0)
  expect(await hasHorizontalScroll(page)).toBe(false)
})

test('the writing pages work by tapping, without sideways scrolling', async ({ page }) => {
  await page.goto('/')
  await fontsReady(page)

  await blogLink(page).tap()
  await expect(page.getByRole('heading', { level: 1, name: 'WRITING' })).toBeVisible()
  expect(await hasHorizontalScroll(page)).toBe(false)

  await page.getByRole('link', { name: POSTS.newest.title }).tap()
  await expect(page.getByRole('heading', { level: 1, name: POSTS.newest.title })).toBeVisible()
  expect(await hasHorizontalScroll(page)).toBe(false)

  await chip(page, CHIPS[0]).tap()
  await expectAnswered(page)
  await expect(conversation(page)).toContainText(CHIPS[0])
})

test('the chips sit on one swipeable line so the footer stays small', async ({ page }) => {
  await page.goto('/')
  await fontsReady(page)

  const tops = await Promise.all(
    CHIPS.map(async (text) => (await chip(page, text).boundingBox())?.y ?? -1),
  )
  expect(new Set(tops).size).toBe(1)

  const row = page.getByRole('group', { name: 'Suggested questions' })
  expect(await row.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true)
})

test('the composer is usable and typing asks a question', async ({ page }) => {
  await page.goto('/')

  await composer(page).fill('typed on a phone')
  await page.getByRole('button', { name: /send/i }).tap()
  await expectAnswered(page)

  await expect(conversation(page)).toContainText('typed on a phone')
  await expect(composer(page)).toBeVisible()
})
