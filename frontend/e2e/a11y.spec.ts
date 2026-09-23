import { AxeBuilder } from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { aboutButton, ask, blogLink, fontsReady, POSTS } from './helpers'

async function violationsOn(page: Page) {
  await fontsReady(page)
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice'])
    .analyze()
  return results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length} node(s))`)
}

test('the welcome screen has no accessibility violations', async ({ page }) => {
  await page.goto('/')
  expect(await violationsOn(page)).toEqual([])
})

test('the conversation has no accessibility violations', async ({ page }) => {
  await page.goto('/')
  await ask(page, 'hello')
  expect(await violationsOn(page)).toEqual([])
})

test('the about popover has no accessibility violations', async ({ page }) => {
  await page.goto('/')
  await ask(page, 'hello')
  await aboutButton(page).click()
  expect(await violationsOn(page)).toEqual([])
})

test('the writing list has no accessibility violations', async ({ page }) => {
  await page.goto('/writing')
  await expect(page.getByRole('heading', { level: 1, name: 'WRITING' })).toBeVisible()
  expect(await violationsOn(page)).toEqual([])
})

test('a post has no accessibility violations', async ({ page }) => {
  await page.goto(`/writing/${POSTS.newest.slug}`)
  await expect(page.getByRole('heading', { level: 1, name: POSTS.newest.title })).toBeVisible()
  expect(await violationsOn(page)).toEqual([])
})

test('the writing pages have no accessibility violations after a conversation', async ({
  page,
}) => {
  await page.goto('/')
  await ask(page, 'hello')
  await blogLink(page).click()
  await expect(page.getByRole('heading', { level: 1, name: 'WRITING' })).toBeVisible()
  expect(await violationsOn(page)).toEqual([])
})

test('the not-found messages have no accessibility violations', async ({ page }) => {
  await page.goto('/writing/no-such-post')
  await expect(page.getByText('There is no post at this address.')).toBeVisible()
  expect(await violationsOn(page)).toEqual([])
})

test('the error state has no accessibility violations', async ({ page }) => {
  await page.route('**/api/chat', (route) => route.fulfill({ status: 500, json: { detail: 'x' } }))
  await page.goto('/')
  await page.getByRole('textbox', { name: 'Ask me something' }).fill('hello')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'try again' })).toBeVisible()
  expect(await violationsOn(page)).toEqual([])
})
