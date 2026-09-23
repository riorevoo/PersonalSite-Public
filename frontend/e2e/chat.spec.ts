import { expect, test } from '@playwright/test'
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
  startOver,
} from './helpers'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
})

test.describe('welcome screen', () => {
  test('shows the profile, the three chips and the composer, without a photo block', async ({
    page,
  }) => {
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    // The top bar is always there with the blog and about buttons; the name and "start over"
    // only appear once a question has been asked.
    await expect(blogLink(page)).toBeVisible()
    await expect(aboutButton(page)).toBeVisible()
    await expect(startOver(page)).toHaveCount(0)
    for (const text of CHIPS) await expect(chip(page, text)).toBeVisible()
    await expect(composer(page)).toBeVisible()
    await expect(composer(page)).toHaveAttribute('placeholder', 'ask me something')
    // No "PHOTO OF ME" block: the only picture is the small inline "mini me" in the note.
    await expect(page.getByRole('img')).toHaveCount(1)
    await expect(page.getByRole('img')).toHaveAccessibleName('my mini me')
    await expect(page.getByText(/photo of me/i)).toHaveCount(0)
  })

  test('has no console errors or failed requests on load', async ({ page }) => {
    const problems: string[] = []
    page.on('console', (message) => message.type() === 'error' && problems.push(message.text()))
    page.on('requestfailed', (request) => problems.push(`failed: ${request.url()}`))

    await page.reload()
    await page.waitForLoadState('networkidle')

    expect(problems).toEqual([])
  })
})

test.describe('asking questions', () => {
  for (const text of CHIPS) {
    test(`clicking the chip "${text}" asks it and shows an answer`, async ({ page }) => {
      await chip(page, text).click()
      await expectAnswered(page)

      await expect(conversation(page)).toContainText(text)
      await expect(page.getByRole('banner')).toBeVisible()
      await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1) // now the name
    })
  }

  test('a chip fills the text box first, then sends what is in it', async ({ page }) => {
    // Freeze the page's clock so the short pause between filling and sending can be inspected.
    await page.clock.install({ time: new Date('2026-01-01T08:00:00') })
    await page.goto('/')
    await page.clock.pauseAt(new Date('2026-01-01T08:00:10'))

    await chip(page, CHIPS[0]).click()

    await expect(composer(page)).toHaveValue(CHIPS[0])
    await expect(composer(page)).toHaveAttribute('readonly', '')
    await expect(conversation(page)).toHaveCount(0) // nothing has been sent yet

    await page.clock.runFor(1000)
    await expectAnswered(page)

    await expect(conversation(page)).toContainText(CHIPS[0])
    await expect(composer(page)).toHaveValue('')
    await expect(composer(page)).not.toHaveAttribute('readonly', '')
  })

  test('a chip sends exactly the text it put in the box', async ({ page }) => {
    const messages: string[] = []
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().endsWith('/api/chat')) {
        messages.push(request.postDataJSON().message)
      }
    })

    await chip(page, CHIPS[2]).click()
    await expectAnswered(page)

    expect(messages).toEqual([CHIPS[2]])
  })

  test('typing a question and pressing Enter asks it and clears the field', async ({ page }) => {
    await ask(page, 'do you like tea?')

    await expect(conversation(page)).toContainText('do you like tea?')
    await expect(composer(page)).toHaveValue('')
  })

  test('the SEND button asks the question too', async ({ page }) => {
    await composer(page).fill('via the button')
    await page.getByRole('button', { name: /send/i }).click()
    await expectAnswered(page)

    await expect(conversation(page)).toContainText('via the button')
  })

  test('an empty or whitespace question does nothing', async ({ page }) => {
    await composer(page).press('Enter')
    await composer(page).fill('    ')
    await composer(page).press('Enter')

    await expect(startOver(page)).toHaveCount(0)
    await expect(conversation(page)).toHaveCount(0)
  })

  test('keeps the conversation and sends earlier turns along as history', async ({ page }) => {
    const bodies: { message: string; history: { role: string; content: string }[] }[] = []
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().endsWith('/api/chat')) {
        bodies.push(request.postDataJSON())
      }
    })

    await ask(page, 'first question')
    await ask(page, 'second question')

    await expect(conversation(page)).toContainText('first question')
    await expect(conversation(page)).toContainText('second question')
    expect(bodies).toHaveLength(2)
    expect(bodies[0]?.history).toEqual([])
    expect(bodies[1]?.history.map((turn) => turn.role)).toEqual(['user', 'assistant'])
    expect(bodies[1]?.history[0]?.content).toBe('first question')
  })

  test('can be driven entirely from the keyboard', async ({ page }) => {
    await chip(page, CHIPS[1]).focus()
    await page.keyboard.press('Enter')
    await expectAnswered(page)
    await expect(conversation(page)).toContainText(CHIPS[1])

    await composer(page).focus()
    await page.keyboard.type('and a typed one')
    await page.keyboard.press('Enter')
    await expectAnswered(page)
    await expect(conversation(page)).toContainText('and a typed one')
  })
})

test.describe('start over', () => {
  test('returns to the welcome screen and clears the conversation', async ({ page }) => {
    await ask(page, 'something to forget')

    await startOver(page).click()

    await expect(startOver(page)).toHaveCount(0)
    await expect(page.getByText('something to forget')).toHaveCount(0)
    await expect(chip(page, CHIPS[0])).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })
})

test.describe('about me', () => {
  test.beforeEach(async ({ page }) => {
    await ask(page, 'hello')
  })

  test('opens from the top right and closes from the same button', async ({ page }) => {
    await aboutButton(page).click()
    await expect(aboutDialog(page)).toBeVisible()
    await expect(aboutButton(page)).toHaveAttribute('aria-expanded', 'true')

    await aboutButton(page).click()
    await expect(aboutDialog(page)).toHaveCount(0)
    await expect(aboutButton(page)).toBeFocused()
  })

  test('closes with the close button and returns focus to the trigger', async ({ page }) => {
    await aboutButton(page).click()
    await page.getByRole('button', { name: 'Close' }).click()

    await expect(aboutDialog(page)).toHaveCount(0)
    await expect(aboutButton(page)).toBeFocused()
  })

  test('closes with Escape', async ({ page }) => {
    await aboutButton(page).click()
    await page.keyboard.press('Escape')
    await expect(aboutDialog(page)).toHaveCount(0)
  })

  test('closes when clicking outside it', async ({ page }) => {
    await aboutButton(page).click()
    await conversation(page).click({ position: { x: 5, y: 5 } })
    await expect(aboutDialog(page)).toHaveCount(0)
  })

  test('closes when a question is asked from the keyboard', async ({ page }) => {
    await aboutButton(page).click()
    // Focus and type without clicking: a click anywhere else would close the popover by itself
    // (it is an outside click), which would hide a missing close-on-ask.
    await composer(page).focus()
    await page.keyboard.type('asked with the keyboard')
    await page.keyboard.press('Enter')

    await expect(aboutDialog(page)).toHaveCount(0)
    await expectAnswered(page)
  })

  test('closes when a suggestion chip is asked', async ({ page }) => {
    await aboutButton(page).click()
    await chip(page, CHIPS[2]).click()
    await expect(aboutDialog(page)).toHaveCount(0)
    await expectAnswered(page)
  })

  test('shows the profile without a photo', async ({ page }) => {
    await aboutButton(page).click()
    const dialog = aboutDialog(page)

    await expect(dialog).toContainText('status')
    await expect(dialog.getByRole('link').first()).toBeVisible()
    await expect(dialog.getByRole('img')).toHaveCount(0)
  })
})

test.describe('when the service misbehaves', () => {
  test('shows a friendly error and recovers when retrying', async ({ page }) => {
    let calls = 0
    await page.route('**/api/chat', (route) => {
      calls += 1
      return calls === 1
        ? route.fulfill({ status: 500, json: { detail: 'boom' } })
        : route.continue()
    })

    await chip(page, CHIPS[0]).click()
    await expect(conversation(page)).toContainText('could not reach my answering service')

    await page.getByRole('button', { name: 'try again' }).click()
    await expectAnswered(page)
    expect(calls).toBe(2)
  })

  test('says so plainly when the visitor is rate limited', async ({ page }) => {
    await page.route('**/api/chat', (route) =>
      route.fulfill({
        status: 429,
        headers: { 'Retry-After': '30' },
        json: { detail: 'Too many questions.' },
      }),
    )

    await chip(page, CHIPS[0]).click()

    await expect(conversation(page)).toContainText("You're asking faster than I can answer")
    await expect(page.getByRole('button', { name: 'try again' })).toBeVisible()
  })

  test('treats an unavailable answering engine (503) as a retryable error', async ({ page }) => {
    await page.route('**/api/chat', (route) =>
      route.fulfill({ status: 503, json: { detail: 'The answering service is unavailable.' } }),
    )

    await chip(page, CHIPS[0]).click()

    await expect(conversation(page)).toContainText('could not reach my answering service')
    await expect(page.getByRole('button', { name: 'try again' })).toBeVisible()
  })

  test('shows the spend-cap message as a normal answer, with no error and no retry', async ({
    page,
  }) => {
    const capMessage =
      "Someone asked me too many questions this month; Site Owner doesn't pay enough for me to answer more. Sorry!"
    await page.route('**/api/chat', (route) => route.fulfill({ json: { answer: capMessage } }))

    await ask(page, 'anything at all')

    await expect(conversation(page)).toContainText(capMessage)
    await expect(conversation(page)).not.toContainText('could not reach my answering service')
    await expect(page.getByRole('button', { name: 'try again' })).toHaveCount(0)
  })

  test('shows a thinking state while waiting, and the chips are inert meanwhile', async ({
    page,
  }) => {
    let release: () => void = () => {}
    const gate = new Promise<void>((resolve) => (release = resolve))
    await page.route('**/api/chat', async (route) => {
      await gate
      await route.continue()
    })

    await chip(page, CHIPS[0]).click()

    await expect(page.getByRole('status')).toContainText('thinking')
    await expect(chip(page, CHIPS[1])).toHaveAttribute('aria-disabled', 'true')
    await chip(page, CHIPS[1]).click({ force: true })
    await expect(conversation(page).getByText(CHIPS[1])).toHaveCount(0)

    release()
    await expectAnswered(page)
    await expect(chip(page, CHIPS[1])).toHaveAttribute('aria-disabled', 'false')
  })
})
