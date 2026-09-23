import { expect, test } from '@playwright/test'

const picture = (page: import('@playwright/test').Page) =>
  page.getByRole('img', { name: 'my mini me' })

test.beforeEach(async ({ page }) => {
  await page.goto('/')
})

test.describe('the mini me picture', () => {
  test('loads, and is favicon sized on screen', async ({ page }) => {
    await expect(picture(page)).toBeVisible()

    const shown = await picture(page).evaluate((img: HTMLImageElement) => ({
      loaded: img.complete && img.naturalWidth > 0,
      width: img.getBoundingClientRect().width,
      height: img.getBoundingClientRect().height,
    }))

    expect(shown.loaded).toBe(true)
    expect(shown.width).toBeLessThanOrEqual(32)
    expect(shown.height).toBeLessThanOrEqual(32)
  })

  test('stands in for the words "mini me" in "This is my ...", in the same line', async ({
    page,
  }) => {
    const around = await picture(page).evaluate((img) => ({
      before: img.previousSibling?.textContent ?? '',
      after: img.nextSibling?.textContent ?? '',
      sameParagraph: img.parentElement?.tagName === 'P',
    }))

    expect(around.sameParagraph).toBe(true)
    expect(around.before).toMatch(/This is my $/)
    expect(around.after).toMatch(/^\. It knows a bit about me/)
  })

  test('is a small square file, not the full-size picture', async ({ page }) => {
    const response = await page.request.get('/minime.png')
    const bytes = await response.body()

    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toBe('image/png')
    const width = bytes.readUInt32BE(16)
    const height = bytes.readUInt32BE(20)
    expect(width).toBe(height)
    expect(width).toBeLessThanOrEqual(128) // favicon sized (twice 32px, for sharp screens)
    expect(bytes.length).toBeLessThan(50_000)
  })

  test('is not there once a conversation has started, like the rest of the welcome copy', async ({
    page,
  }) => {
    await page.getByRole('textbox', { name: 'Ask me something' }).fill('hello')
    await page.keyboard.press('Enter')
    await expect(page.getByRole('log', { name: 'Conversation' })).toBeVisible()

    await expect(picture(page)).toHaveCount(0)
  })
})
