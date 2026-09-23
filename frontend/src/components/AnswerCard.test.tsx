import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AnswerCard } from './AnswerCard'

describe('AnswerCard', () => {
  it('labels the card as coming from the owner', () => {
    render(<AnswerCard status="done" text="an answer" />)
    expect(screen.getByText('◆ me')).toBeInTheDocument()
  })

  it('shows the answer text when done, with no retry button', () => {
    render(<AnswerCard status="done" text="I build backends." />)
    expect(screen.getByText('I build backends.')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows an accessible thinking state while pending', () => {
    render(<AnswerCard status="pending" text="" />)
    expect(screen.getByRole('status')).toHaveTextContent('thinking')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows the error text and a working retry button on failure', async () => {
    const onRetry = vi.fn()
    render(<AnswerCard status="error" text="Something failed." onRetry={onRetry} />)

    expect(screen.getByText('Something failed.')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'try again' }))

    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('keeps focus in the card after retry, because the retry button goes away', async () => {
    const onRetry = vi.fn()
    const { container } = render(<AnswerCard status="error" text="Failed." onRetry={onRetry} />)

    await userEvent.setup().click(screen.getByRole('button', { name: 'try again' }))

    expect(container.firstElementChild).toHaveFocus()
  })

  it('does not fail when retry is clicked without a handler', async () => {
    render(<AnswerCard status="error" text="Failed." />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'try again' }))
    expect(screen.getByText('Failed.')).toBeInTheDocument()
  })

  it('renders answer text literally, not as markup', () => {
    render(<AnswerCard status="done" text="<script>alert(1)</script>" />)
    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument()
  })
})
