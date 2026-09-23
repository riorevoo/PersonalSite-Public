import { expect, test } from '@playwright/test'

test.describe('the favicon', () => {
  test('is declared by the page and served as a PNG', async ({ page }) => {
    await page.goto('/')

    const icon = page.locator('link[rel="icon"]')
    await expect(icon).toHaveAttribute('href', '/favicon.png')
    await expect(icon).toHaveAttribute('type', 'image/png')

    const response = await page.request.get('/favicon.png')
    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toBe('image/png')
  })

  test('is a square picture, so a browser tab does not squeeze it', async ({ page }) => {
    const bytes = await (await page.request.get('/favicon.png')).body()

    // A PNG starts with an 8 byte signature, then the IHDR chunk: width and height as 32-bit numbers.
    expect(bytes.subarray(1, 4).toString('ascii')).toBe('PNG')
    const width = bytes.readUInt32BE(16)
    const height = bytes.readUInt32BE(20)
    expect(width).toBe(height)
    expect(width).toBeGreaterThanOrEqual(48) // sharp on a high-density tab
  })

  test('no longer serves the old svg icon', async ({ page }) => {
    await page.goto('/')

    await expect(page.locator('link[rel="icon"][href$=".svg"]')).toHaveCount(0)
  })
})
