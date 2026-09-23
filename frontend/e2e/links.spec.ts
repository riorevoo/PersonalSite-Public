import { expect, test } from '@playwright/test'
import { aboutButton, aboutDialog, githubLink, resumeLink } from './helpers'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
})

test.describe('the github link', () => {
  test('goes to the owner’s github, in a new tab', async ({ page }) => {
    await expect(githubLink(page)).toHaveAttribute('href', 'https://github.com/your-username')
    await expect(githubLink(page)).toHaveAttribute('target', '_blank')
    await expect(githubLink(page)).toHaveAttribute('rel', /noopener/)
  })
})

test.describe('the resume link', () => {
  test('opens in a new tab', async ({ page }) => {
    await expect(resumeLink(page)).toHaveAttribute('target', '_blank')
    await expect(resumeLink(page)).toHaveAttribute('rel', /noopener/)

    const popup = page.waitForEvent('popup')
    await resumeLink(page).click()

    // A new tab opened; the current page stayed where it was.
    await expect(await popup).toBeTruthy()
    expect(page.url()).toBe('http://127.0.0.1:4173/')
  })

  test('serves the newest resume PDF for the browser to show', async ({ page }) => {
    const href = await resumeLink(page).getAttribute('href')
    const response = await page.request.get(href!)

    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toBe('application/pdf')
    expect(response.headers()['content-disposition']).toMatch(/^inline/)
    const body = (await response.body()).toString('latin1')
    expect(body).toContain('NEWEST made-up resume')
    expect(body).not.toContain('OLD made-up resume')
  })

  test('is also there in the about popover, and works the same', async ({ page }) => {
    await aboutButton(page).click()
    const link = aboutDialog(page).getByRole('link', { name: '→ résumé (pdf)' })

    await expect(link).toHaveAttribute('href', '/api/resume')
    await expect(link).toHaveAttribute('target', '_blank')
  })
})
