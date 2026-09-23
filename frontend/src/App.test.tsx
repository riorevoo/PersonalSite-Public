import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { profile } from './content/profile'
import { ERROR_TEXT } from './hooks/useChat'
import { detail, stubApi, summary } from './test/posts'

function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

function stubAnswers(...answers: string[]) {
  const fetchMock = vi.fn()
  for (const answer of answers) {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ answer }), { status: 200 }))
  }
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const chip = (index: number) => profile.suggestions[index] ?? ''

describe('App', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('starts on the welcome screen with the blog and about buttons but no name or "start over"', () => {
    renderApp()

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('banner')).not.toHaveTextContent(profile.name)
    expect(screen.getByRole('link', { name: '✎ blog' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '◆ about me' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'start over' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /\?$/ })).toHaveLength(profile.suggestions.length)
    expect(screen.getByRole('textbox', { name: 'Ask me something' })).toBeInTheDocument()
  })

  it('asks a suggested question when its chip is clicked', async () => {
    const fetchMock = stubAnswers('I have done things.')
    renderApp()

    await userEvent.setup().click(screen.getByRole('button', { name: chip(0) }))

    expect(await screen.findByText('I have done things.')).toBeInTheDocument()
    expect(screen.getByText(chip(0), { selector: 'p' })).toBeInTheDocument()
    expect(screen.queryByText(profile.headline.highlight)).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(profile.name)
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('puts a clicked chip in the text box first, then sends it and empties the box', async () => {
    const fetchMock = stubAnswers('An answer.')
    renderApp()
    const box = screen.getByRole('textbox', { name: 'Ask me something' })

    await userEvent.setup().click(screen.getByRole('button', { name: chip(1) }))

    // The question is visible in the box, and locked, before anything has been sent.
    expect(box).toHaveValue(chip(1))
    expect(box).toHaveAttribute('readonly')
    expect(fetchMock).not.toHaveBeenCalled()

    expect(await screen.findByText('An answer.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toMatchObject({
      message: chip(1),
    })
    expect(box).toHaveValue('')
    expect(box).not.toHaveAttribute('readonly')
  })

  it('ignores a second chip clicked while the first is still being filled in', async () => {
    const fetchMock = stubAnswers('Only one.')
    renderApp()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: chip(0) }))
    await user.click(screen.getByRole('button', { name: chip(2) }))

    expect(screen.getByRole('textbox', { name: 'Ask me something' })).toHaveValue(chip(0))
    await screen.findByText('Only one.')
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('lets the visitor type a question and send it as before', async () => {
    stubAnswers('Fine.')
    renderApp()
    const user = userEvent.setup()

    await user.type(screen.getByRole('textbox'), 'a typed one')
    expect(screen.getByRole('textbox')).not.toHaveAttribute('readonly')
    await user.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText('Fine.')).toBeInTheDocument()
  })

  it('asks a typed question with Enter', async () => {
    stubAnswers('Typed answer.')
    renderApp()

    await userEvent.setup().type(screen.getByRole('textbox'), 'what is your name?{Enter}')

    expect(await screen.findByText('Typed answer.')).toBeInTheDocument()
    expect(screen.getByText('what is your name?')).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toHaveValue('')
  })

  it('shows the name and "start over" once the conversation has started', async () => {
    stubAnswers('answer')
    renderApp()

    await userEvent.setup().click(screen.getByRole('button', { name: chip(0) }))
    await screen.findByText('answer')

    expect(screen.getByRole('banner')).toHaveTextContent(profile.name)
    expect(screen.getByRole('button', { name: 'start over' })).toBeInTheDocument()
  })

  it('disables the chips and SEND while an answer is pending', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    renderApp()

    await userEvent.setup().click(screen.getByRole('button', { name: chip(0) }))

    // Already inert while the chip's question sits in the box, and still while it is answered.
    expect(screen.getByRole('button', { name: chip(1) })).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByRole('button', { name: /send/i })).toHaveAttribute('aria-disabled', 'true')
    expect(await screen.findByRole('status')).toHaveTextContent('thinking')
    expect(screen.getByRole('button', { name: chip(1) })).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByRole('button', { name: /send/i })).toHaveAttribute('aria-disabled', 'true')
  })

  it('shows a friendly error with a retry that recovers', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ answer: 'Back online.' })))
    vi.stubGlobal('fetch', fetchMock)
    renderApp()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: chip(0) }))
    expect(await screen.findByText(ERROR_TEXT)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'try again' }))

    expect(await screen.findByText('Back online.')).toBeInTheDocument()
    expect(screen.queryByText(ERROR_TEXT)).not.toBeInTheDocument()
  })

  it('"start over" returns to the welcome screen', async () => {
    stubAnswers('answer')
    renderApp()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: chip(0) }))
    await screen.findByText('answer')
    await user.click(screen.getByRole('button', { name: 'start over' }))

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'start over' })).not.toBeInTheDocument()
    expect(screen.queryByText('answer')).not.toBeInTheDocument()
  })

  describe('about me', () => {
    async function startConversation() {
      stubAnswers('first answer', 'second answer')
      renderApp()
      const user = userEvent.setup()
      await user.click(screen.getByRole('button', { name: chip(0) }))
      await screen.findByText('first answer')
      return user
    }

    it('opens from the top right and closes with the same button', async () => {
      const user = await startConversation()
      const trigger = screen.getByRole('button', { name: '◆ about me' })

      await user.click(trigger)
      expect(screen.getByRole('dialog', { name: 'About me' })).toBeInTheDocument()
      expect(trigger).toHaveAttribute('aria-expanded', 'true')

      await user.click(trigger)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(trigger).toHaveFocus()
    })

    it('opens from the welcome screen too', async () => {
      renderApp()

      await userEvent.setup().click(screen.getByRole('button', { name: '◆ about me' }))

      expect(screen.getByRole('dialog', { name: 'About me' })).toBeInTheDocument()
    })

    it('closes with the close button and returns focus to the trigger', async () => {
      const user = await startConversation()
      await user.click(screen.getByRole('button', { name: '◆ about me' }))

      await user.click(screen.getByRole('button', { name: 'Close' }))

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: '◆ about me' })).toHaveFocus()
    })

    it('closes with Escape', async () => {
      const user = await startConversation()
      await user.click(screen.getByRole('button', { name: '◆ about me' }))

      await user.keyboard('{Escape}')

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('closes when a question is asked from the keyboard', async () => {
      const user = await startConversation()
      await user.click(screen.getByRole('button', { name: '◆ about me' }))

      // Focus and type without clicking: a click elsewhere closes the popover on its own (it is an
      // outside click), which would hide a missing close-on-ask.
      screen.getByRole('textbox', { name: 'Ask me something' }).focus()
      await user.keyboard('asked with the keyboard{Enter}')

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(await screen.findByText('second answer')).toBeInTheDocument()
    })

    it('closes when a suggestion chip is asked', async () => {
      const user = await startConversation()
      await user.click(screen.getByRole('button', { name: '◆ about me' }))

      await user.click(screen.getByRole('button', { name: chip(1) }))

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(await screen.findByText('second answer')).toBeInTheDocument()
    })

    it('closes on "start over"', async () => {
      const user = await startConversation()
      await user.click(screen.getByRole('button', { name: '◆ about me' }))

      await user.click(screen.getByRole('button', { name: 'start over' }))

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('closes when the blog is opened', async () => {
      vi.stubGlobal('fetch', stubApi({ '/api/posts': [] }))
      renderApp()
      const user = userEvent.setup()
      await user.click(screen.getByRole('button', { name: '◆ about me' }))

      await user.click(screen.getByRole('link', { name: '✎ blog' }))

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  describe('writing', () => {
    const posts = [summary({ slug: 'a-post', title: 'The pool that never drained' })]

    it('opens the writing list from the top bar, without the chips and composer', async () => {
      vi.stubGlobal('fetch', stubApi({ '/api/posts': posts }))
      renderApp()

      await userEvent.setup().click(screen.getByRole('link', { name: '✎ blog' }))

      expect(
        await screen.findByRole('heading', { level: 1, name: profile.writing.heading }),
      ).toBeInTheDocument()
      expect(
        await screen.findByRole('link', { name: 'The pool that never drained' }),
      ).toBeInTheDocument()
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
      expect(screen.queryByRole('contentinfo')).not.toBeInTheDocument()
    })

    it('opens a post from the list', async () => {
      vi.stubGlobal(
        'fetch',
        stubApi({
          '/api/posts': posts,
          '/api/posts/a-post': detail({ slug: 'a-post', title: 'The pool that never drained' }),
        }),
      )
      renderApp('/writing')
      const user = userEvent.setup()

      await user.click(await screen.findByRole('link', { name: 'The pool that never drained' }))

      expect(
        await screen.findByRole('heading', { level: 1, name: 'The pool that never drained' }),
      ).toBeInTheDocument()
    })

    it('can be opened directly at a post address', async () => {
      vi.stubGlobal('fetch', stubApi({ '/api/posts/a-post': detail({ title: 'Direct link' }) }))
      renderApp('/writing/a-post')

      expect(
        await screen.findByRole('heading', { level: 1, name: 'Direct link' }),
      ).toBeInTheDocument()
    })

    it('has one page heading: the top bar name is plain text off the chat page', async () => {
      vi.stubGlobal('fetch', stubApi({ '/api/chat': { answer: 'an answer' }, '/api/posts': posts }))
      renderApp()
      const user = userEvent.setup()
      await user.click(screen.getByRole('button', { name: chip(0) }))
      await screen.findByText('an answer')

      await user.click(screen.getByRole('link', { name: '✎ blog' }))

      await screen.findByRole('heading', { level: 1, name: profile.writing.heading })
      expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
      expect(screen.getByRole('banner')).toHaveTextContent(profile.name)
    })

    it('keeps the conversation when you visit the writing and come back', async () => {
      vi.stubGlobal('fetch', stubApi({ '/api/chat': { answer: 'an answer' }, '/api/posts': posts }))
      renderApp()
      const user = userEvent.setup()
      await user.click(screen.getByRole('button', { name: chip(0) }))
      await screen.findByText('an answer')

      await user.click(screen.getByRole('link', { name: '✎ blog' }))
      await screen.findByRole('heading', { level: 1, name: profile.writing.heading })
      await user.click(screen.getByRole('link', { name: '← back to asking' }))

      expect(screen.getByText('an answer')).toBeInTheDocument()
      expect(screen.getByRole('textbox', { name: 'Ask me something' })).toBeInTheDocument()
    })

    it('asking from a post goes to the conversation with the answer', async () => {
      vi.stubGlobal(
        'fetch',
        stubApi({
          '/api/chat': { answer: 'the answer' },
          '/api/posts/a-post': detail({ slug: 'a-post' }),
        }),
      )
      renderApp('/writing/a-post')
      const user = userEvent.setup()

      await user.click(await screen.findByRole('button', { name: chip(0) }))

      expect(await screen.findByText('the answer')).toBeInTheDocument()
      expect(screen.getByRole('textbox', { name: 'Ask me something' })).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: '← all writing' })).not.toBeInTheDocument()
    })

    it('offers two of the suggestion chips under a post', async () => {
      vi.stubGlobal('fetch', stubApi({ '/api/posts/a-post': detail({ slug: 'a-post' }) }))
      renderApp('/writing/a-post')

      await screen.findByRole('complementary', { name: 'Ask about this post' })

      expect(screen.getAllByRole('button', { name: /\?$/ })).toHaveLength(2)
    })

    it('says so for an address the site does not have', () => {
      renderApp('/nowhere')

      expect(screen.getByText('There is nothing at this address.')).toBeInTheDocument()
    })
  })
})
