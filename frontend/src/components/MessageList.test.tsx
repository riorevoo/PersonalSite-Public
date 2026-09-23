import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Message } from '../hooks/useChat'
import { MessageList } from './MessageList'

const messages: Message[] = [
  { id: 1, question: 'first?', answer: 'first answer', status: 'done' },
  { id: 2, question: 'second?', answer: '', status: 'pending' },
  { id: 3, question: 'third?', answer: 'It failed.', status: 'error' },
]

describe('MessageList', () => {
  const scrollIntoView = vi.fn()

  beforeEach(() => {
    scrollIntoView.mockClear()
    // jsdom does not implement scrollIntoView.
    Element.prototype.scrollIntoView = scrollIntoView
  })

  it('shows every question with its answer state in order', () => {
    render(<MessageList messages={messages} onRetry={vi.fn()} />)

    expect(screen.getByRole('log', { name: 'Conversation' })).toBeInTheDocument()
    expect(screen.getByText('first?')).toBeInTheDocument()
    expect(screen.getByText('first answer')).toBeInTheDocument()
    expect(screen.getByText('second?')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('thinking')
    expect(screen.getByText('It failed.')).toBeInTheDocument()
  })

  it('retries the failed message by id', async () => {
    const onRetry = vi.fn()
    render(<MessageList messages={messages} onRetry={onRetry} />)

    await userEvent.setup().click(screen.getByRole('button', { name: 'try again' }))

    expect(onRetry).toHaveBeenCalledExactlyOnceWith(3)
  })

  it('scrolls the newest message into view when messages change', () => {
    const { rerender } = render(<MessageList messages={messages.slice(0, 1)} onRetry={vi.fn()} />)
    expect(scrollIntoView).toHaveBeenCalledTimes(1)

    rerender(<MessageList messages={messages} onRetry={vi.fn()} />)

    expect(scrollIntoView).toHaveBeenCalledTimes(2)
    expect(scrollIntoView).toHaveBeenLastCalledWith({ block: 'end' })
  })

  it('shows a short answer with the newest exchange pinned to the bottom', () => {
    render(<MessageList messages={messages.slice(0, 1)} onRetry={vi.fn()} />)

    const [exchange] = scrollIntoView.mock.contexts as Element[]
    expect(exchange?.textContent).toContain('first answer')
    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'end' })
  })

  it('scrolls a very tall answer to its first line instead of its last', () => {
    vi.spyOn(Element.prototype, 'clientHeight', 'get').mockReturnValue(500)
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ height: 900 } as DOMRect)

    render(<MessageList messages={messages.slice(0, 1)} onRetry={vi.fn()} />)

    expect(scrollIntoView).toHaveBeenCalledExactlyOnceWith({ block: 'start' })
    const [target] = scrollIntoView.mock.contexts as Element[]
    expect(target?.textContent).toContain('first answer')
    expect(target?.textContent).not.toContain('first?')
    vi.restoreAllMocks()
  })

  it('measures an answer against the scroll area (main), even with a wrapper in between', () => {
    vi.spyOn(Element.prototype, 'clientHeight', 'get').mockImplementation(function (this: Element) {
      return this.tagName === 'MAIN' ? 500 : 5000
    })
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ height: 900 } as DOMRect)

    render(
      <main>
        <div>
          <MessageList messages={messages.slice(0, 1)} onRetry={vi.fn()} />
        </div>
      </main>,
    )

    // 900 is taller than main (500), though shorter than the wrapper (5000): show its first line.
    expect(scrollIntoView).toHaveBeenCalledExactlyOnceWith({ block: 'start' })
    vi.restoreAllMocks()
  })

  it('renders an empty log and does not scroll when there are no messages', () => {
    render(<MessageList messages={[]} onRetry={vi.fn()} />)

    expect(screen.getByRole('log')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(scrollIntoView).not.toHaveBeenCalled()
  })
})
