import { expect, test } from '@playwright/test'
import {
  aboutButton,
  aboutDialog,
  ask,
  blogLink,
  composer,
  fontsReady,
  hasHorizontalScroll,
  POSTS,
} from './helpers'

const viewports = [
  { name: 'small phone', width: 360, height: 700 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'laptop', width: 1160, height: 822 },
  { name: 'wide desktop', width: 1920, height: 1080 },
]

for (const { name, width, height } of viewports) {
  test.describe(`${name} (${width}x${height})`, () => {
    test.use({ viewport: { width, height } })

    test('welcome screen does not scroll sideways and keeps the composer on screen', async ({
      page,
    }) => {
      await page.goto('/')
      await fontsReady(page)

      expect(await hasHorizontalScroll(page)).toBe(false)
      const box = await composer(page).boundingBox()
      expect(box).not.toBeNull()
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.x + box!.width).toBeLessThanOrEqual(width)
      expect(box!.y + box!.height).toBeLessThanOrEqual(height)
    })

    test('the writing list and a post do not scroll sideways', async ({ page }) => {
      await page.goto('/writing')
      await expect(page.getByRole('heading', { level: 1, name: 'WRITING' })).toBeVisible()
      await fontsReady(page)
      expect(await hasHorizontalScroll(page)).toBe(false)

      await page.goto(`/writing/${POSTS.newest.slug}`)
      await expect(page.getByRole('heading', { level: 1, name: POSTS.newest.title })).toBeVisible()
      await fontsReady(page)
      expect(await hasHorizontalScroll(page)).toBe(false)
    })

    test('the top bar fits with a conversation under way', async ({ page }) => {
      await page.goto('/')
      await ask(page, 'hello')
      await fontsReady(page)

      expect(await hasHorizontalScroll(page)).toBe(false)
      for (const target of [blogLink(page), aboutButton(page)]) {
        const box = await target.boundingBox()
        expect(box).not.toBeNull()
        expect(box!.x).toBeGreaterThanOrEqual(0)
        expect(box!.x + box!.width).toBeLessThanOrEqual(width)
      }
    })

    test('conversation and the about popover stay within the screen', async ({ page }) => {
      await page.goto('/')
      await ask(page, 'hello')
      await aboutButton(page).click()
      await fontsReady(page)

      expect(await hasHorizontalScroll(page)).toBe(false)
      const popover = await aboutDialog(page).boundingBox()
      expect(popover).not.toBeNull()
      expect(popover!.x).toBeGreaterThanOrEqual(0)
      expect(popover!.x + popover!.width).toBeLessThanOrEqual(width)
      expect(popover!.y + popover!.height).toBeLessThanOrEqual(height)
    })
  })
}

test("on a very wide screen the content stays in the design's 1100px column", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/')

  // <main> is the full-width scroll area; its first child is the centred column.
  const column = await page.getByRole('main').locator(':scope > *').first().boundingBox()

  expect(column).not.toBeNull()
  expect(column!.width).toBeLessThanOrEqual(1100)
  expect(column!.x).toBeGreaterThan(200) // centred, not stuck to the left edge
})

test('the scroll area spans the whole window, so its scrollbar is at the window edge', async ({
  page,
}) => {
  // Short enough that the welcome content has to scroll.
  await page.setViewportSize({ width: 1920, height: 420 })
  await page.goto('/')

  const scroll = await page.getByRole('main').evaluate((el) => {
    const box = el.getBoundingClientRect()
    return { left: box.left, right: box.right, overflows: el.scrollHeight > el.clientHeight }
  })

  expect(scroll.overflows).toBe(true)
  expect(scroll.left).toBe(0)
  expect(scroll.right).toBe(1920) // not the right edge of a centred column (about 1510)
})

test('the top bar spans the window, with its content in the 1100px column', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/')

  const bar = await page.getByRole('banner').boundingBox()
  const about = await aboutButton(page).boundingBox()

  expect(bar).toMatchObject({ x: 0, width: 1920 })
  expect(about).not.toBeNull()
  expect(about!.x + about!.width).toBeLessThanOrEqual(1510) // the column's right edge
  expect(about!.x + about!.width).toBeGreaterThan(1400) // and not pushed toward the left
})

test('the top bar carries the same dot grid as the page behind it', async ({ page }) => {
  await page.goto('/')

  const grid = await page.evaluate(() => {
    const bar = getComputedStyle(document.querySelector('header')!)
    const body = getComputedStyle(document.body)
    return {
      bar: { image: bar.backgroundImage, size: bar.backgroundSize },
      body: { image: body.backgroundImage, size: body.backgroundSize },
    }
  })

  expect(grid.bar.image).toContain('radial-gradient')
  expect(grid.bar).toEqual(grid.body)
})

test('the about popover stays under the about button on a very wide screen', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/')
  await aboutButton(page).click()

  const button = await aboutButton(page).boundingBox()
  const popover = await aboutDialog(page).boundingBox()

  expect(button).not.toBeNull()
  expect(popover).not.toBeNull()
  // Right-aligned with the button (within the column's padding), not at the window's far edge.
  expect(Math.abs(popover!.x + popover!.width - (button!.x + button!.width))).toBeLessThan(10)
  expect(popover!.y).toBeGreaterThan(button!.y + button!.height)
})

test('on a short screen the welcome content scrolls instead of being cut off', async ({ page }) => {
  await page.setViewportSize({ width: 1160, height: 420 })
  await page.goto('/')

  const heading = page.getByRole('heading', { level: 1 })
  const main = page.getByRole('main')
  const box = await heading.boundingBox()

  expect(box).not.toBeNull()
  expect(box!.y).toBeGreaterThanOrEqual(0) // the top is reachable, not clipped above the viewport
  expect(await main.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true)
})
