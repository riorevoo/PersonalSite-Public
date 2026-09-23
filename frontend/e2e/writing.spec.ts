import { expect, test, type Page } from '@playwright/test'
import {
  aboutButton,
  aboutDialog,
  ask,
  blogLink,
  CHIPS,
  chip,
  composer,
  conversation,
  expectAnswered,
  POSTS,
} from './helpers'

const heading = (page: Page, name: string) => page.getByRole('heading', { level: 1, name })

test('loads the post module only when a visitor opens a post', async ({ page }) => {
  const postModules: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/src/routes/PostRoute.tsx')) postModules.push(request.url())
  })
  await page.goto('/')
  await expect(composer(page)).toBeVisible()
  await page.waitForLoadState('networkidle')
  expect(postModules).toEqual([])
  await blogLink(page).click()
  await page.getByRole('link', { name: POSTS.newest.title }).click()
  await expect(heading(page, POSTS.newest.title)).toBeVisible()
  expect(postModules).toHaveLength(1)
})

test('recovers from a failed route download by reloading', async ({ page }) => {
  await page.route('**/src/routes/PostRoute.tsx', (route) => route.abort())
  await page.goto(`/writing/${POSTS.newest.slug}`)
  const reload = page.getByRole('link', { name: 'Reload the page' })
  await expect(reload).toBeVisible()
  await page.unroute('**/src/routes/PostRoute.tsx')
  await reload.click()
  await expect(heading(page, POSTS.newest.title)).toBeVisible()
})

test('a hung writing request becomes an error after thirty seconds', async ({ page }) => {
  await page.clock.install()
  await page.route('**/api/posts', () => Promise.resolve())
  const requested = page.waitForRequest('**/api/posts')
  await page.goto('/writing')
  // Wait until the API load has started, not just the route's download fallback.
  await requested
  await expect(page.getByRole('status')).toBeVisible()
  await page.clock.fastForward(30_001)
  await expect(
    page.getByText('I could not load the writing just now. Please try again in a moment.'),
  ).toBeVisible()
})

test.describe('the writing list', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await blogLink(page).click()
  })

  test('opens from the top bar and lists the published posts, newest first', async ({ page }) => {
    await expect(page).toHaveURL(/\/writing$/)
    await expect(heading(page, 'WRITING')).toBeVisible()

    await expect(page.getByRole('heading', { level: 2 })).toHaveText([
      POSTS.newest.title,
      POSTS.oldest.title,
    ])
    await expect(page.getByText('2026 · 08 · 14')).toBeVisible()
    await expect(page.getByText('1 min').first()).toBeVisible()
  })

  test('never shows a draft', async ({ page }) => {
    // Wait for the list itself first: "absent" is true of a list that has not loaded yet.
    await expect(page.getByRole('heading', { level: 2 })).toHaveCount(2)
    await expect(page.getByText(POSTS.draft.title)).toHaveCount(0)
  })

  test('is a page of text: no chips or composer', async ({ page }) => {
    await expect(composer(page)).toHaveCount(0)
    await expect(chip(page, CHIPS[0])).toHaveCount(0)
  })

  test('goes back to asking', async ({ page }) => {
    await page.getByRole('link', { name: '← back to asking' }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(composer(page)).toBeVisible()
  })

  test('has no console errors or failed requests', async ({ page }) => {
    const problems: string[] = []
    page.on('console', (message) => message.type() === 'error' && problems.push(message.text()))
    page.on('requestfailed', (request) => {
      // The page cancels a request on purpose when it leaves or reloads (in dev, React also runs
      // each effect twice): that is not a failure.
      if (request.failure()?.errorText !== 'net::ERR_ABORTED') {
        problems.push(`failed: ${request.url()}`)
      }
    })

    await page.reload()
    await expect(heading(page, 'WRITING')).toBeVisible()
    await page.waitForLoadState('networkidle')

    expect(problems).toEqual([])
  })
})

test.describe('a post', () => {
  test('opens from the list, renders its Markdown, and goes back to all writing', async ({
    page,
  }) => {
    await page.goto('/writing')

    await page.getByRole('link', { name: POSTS.newest.title }).click()

    await expect(page).toHaveURL(new RegExp(`/writing/${POSTS.newest.slug}$`))
    await expect(heading(page, POSTS.newest.title)).toBeVisible()
    await expect(page.getByRole('heading', { level: 2, name: 'What happened' })).toBeVisible()
    await expect(page.getByRole('listitem')).toHaveText([
      'the first list item',
      'the second list item',
    ])
    await expect(page.locator('pre code')).toHaveText('print("hello")')

    await page.getByRole('link', { name: '← all writing' }).click()
    await expect(heading(page, 'WRITING')).toBeVisible()
  })

  test('can be opened directly, and survives a reload', async ({ page }) => {
    await page.goto(`/writing/${POSTS.oldest.slug}`)
    await expect(heading(page, POSTS.oldest.title)).toBeVisible()

    await page.reload()

    await expect(heading(page, POSTS.oldest.title)).toBeVisible()
  })

  test('can be opened from the keyboard', async ({ page }) => {
    await page.goto('/writing')

    await page.getByRole('link', { name: POSTS.oldest.title }).focus()
    await page.keyboard.press('Enter')

    await expect(heading(page, POSTS.oldest.title)).toBeVisible()
  })

  test('says so when there is no post at the address', async ({ page }) => {
    await page.goto('/writing/no-such-post')

    await expect(page.getByText('There is no post at this address.')).toBeVisible()
    await expect(page.getByRole('link', { name: '← all writing' })).toBeVisible()
  })

  test('a draft cannot be reached by its address', async ({ page }) => {
    await page.goto(`/writing/${POSTS.draft.slug}`)

    await expect(page.getByText('There is no post at this address.')).toBeVisible()
    await expect(page.getByText('Unpublished sample text.')).toHaveCount(0)
  })

  test('"ask about this" takes the visitor to the conversation with an answer', async ({
    page,
  }) => {
    await page.goto(`/writing/${POSTS.newest.slug}`)

    const aside = page.getByRole('complementary', { name: 'Ask about this post' })
    await expect(aside.getByRole('button')).toHaveCount(2)
    await aside.getByRole('button', { name: CHIPS[0] }).click()

    await expect(page).toHaveURL(/\/$/)
    await expectAnswered(page)
    await expect(conversation(page)).toContainText(CHIPS[0])
  })
})

test.describe('with a conversation under way', () => {
  test('keeps the conversation when the visitor reads a post and comes back', async ({ page }) => {
    await page.goto('/')
    await ask(page, 'do you like tea?')

    await blogLink(page).click()
    await page.getByRole('link', { name: POSTS.newest.title }).click()
    await expect(heading(page, POSTS.newest.title)).toBeVisible()
    await page.getByRole('link', { name: '← back to asking' }).click()

    await expect(conversation(page)).toContainText('do you like tea?')
    await expect(composer(page)).toBeVisible()
  })

  test('the top bar keeps "start over" and has a single page heading on the writing page', async ({
    page,
  }) => {
    await page.goto('/')
    await ask(page, 'hello')

    await blogLink(page).click()

    await expect(heading(page, 'WRITING')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
    await expect(page.getByRole('button', { name: 'start over' })).toBeVisible()
  })

  test('closes the about popover when the blog is opened', async ({ page }) => {
    await page.goto('/')
    await aboutButton(page).click()
    await expect(aboutDialog(page)).toBeVisible()

    await blogLink(page).click()

    await expect(aboutDialog(page)).toHaveCount(0)
    await expect(heading(page, 'WRITING')).toBeVisible()
  })
})

test('an address the site does not have says so, with a way back', async ({ page }) => {
  await page.goto('/nowhere')

  await expect(page.getByText('There is nothing at this address.')).toBeVisible()
  await page.getByRole('link', { name: '← back to asking' }).click()
  await expect(composer(page)).toBeVisible()
})
