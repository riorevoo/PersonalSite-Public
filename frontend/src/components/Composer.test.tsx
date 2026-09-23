import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { MAX_MESSAGE_CHARS } from '../constants'
import { Composer } from './Composer'

type Props = Partial<React.ComponentProps<typeof Composer>>

/** The parent owns the text, as App does; this stands in for it. */
function Harness({ initial = '', onSubmit, ...rest }: Props & { initial?: string }) {
  const [value, setValue] = useState(initial)
  return <Composer value={value} onChange={setValue} onSubmit={onSubmit ?? vi.fn()} {...rest} />
}

function setup(props: Props & { initial?: string } = {}) {
  const onSubmit = vi.fn()
  render(<Harness onSubmit={onSubmit} {...props} />)
  return {
    onSubmit,
    input: screen.getByRole('textbox', { name: 'Ask me something' }),
    user: userEvent.setup(),
  }
}

describe('Composer', () => {
  it('submits the trimmed text on Enter and clears the field', async () => {
    const { onSubmit, input, user } = setup()

    await user.type(input, '  hello there  {Enter}')

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith('hello there')
    expect(input).toHaveValue('')
  })

  it('submits when the SEND button is clicked', async () => {
    const { onSubmit, input, user } = setup()

    await user.type(input, 'via button')
    await user.click(screen.getByRole('button', { name: /send/i }))

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith('via button')
  })

  it('keeps focus in the input after sending', async () => {
    const { input, user } = setup()

    await user.type(input, 'hi')
    await user.click(screen.getByRole('button', { name: /send/i }))

    expect(input).toHaveFocus()
  })

  it('ignores empty and whitespace-only input', async () => {
    const { onSubmit, input, user } = setup()

    await user.click(screen.getByRole('button', { name: /send/i }))
    await user.type(input, '   {Enter}')

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows the text it is given, so a suggested question can be put in the box', () => {
    const { input } = setup({ initial: 'what experience do you have?' })

    expect(input).toHaveValue('what experience do you have?')
  })

  it('reports each keystroke to its parent', async () => {
    const onChange = vi.fn()
    render(<Composer value="" onChange={onChange} onSubmit={vi.fn()} />)

    await userEvent.setup().type(screen.getByRole('textbox'), 'ab')

    expect(onChange).toHaveBeenNthCalledWith(1, 'a')
    expect(onChange).toHaveBeenNthCalledWith(2, 'b')
  })

  it('cannot be edited while it is being filled for the visitor', async () => {
    const { input, user } = setup({ initial: 'a suggestion', readOnly: true })

    await user.type(input, 'more')

    expect(input).toHaveAttribute('readonly')
    expect(input).toHaveValue('a suggestion')
  })

  it('does not submit while disabled but keeps the draft', async () => {
    const { onSubmit, input, user } = setup({ disabled: true })

    await user.type(input, 'wait for me{Enter}')

    expect(screen.getByRole('button', { name: /send/i })).toHaveAttribute('aria-disabled', 'true')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(input).toHaveValue('wait for me')
  })

  it('ignores a click on SEND while disabled and keeps focus on it', async () => {
    const { onSubmit, input, user } = setup({ disabled: true })
    await user.type(input, 'queued')

    const send = screen.getByRole('button', { name: /send/i })
    await user.click(send)

    expect(onSubmit).not.toHaveBeenCalled()
    expect(send).toHaveFocus()
  })

  it('does not submit a draft typed before disabling, even via the form', async () => {
    const onSubmit = vi.fn()
    const { rerender } = render(<Composer value="draft" onChange={vi.fn()} onSubmit={onSubmit} />)
    const input = screen.getByRole('textbox', { name: 'Ask me something' })

    rerender(<Composer value="draft" onChange={vi.fn()} onSubmit={onSubmit} disabled />)
    input.closest('form')?.requestSubmit()

    expect(onSubmit).not.toHaveBeenCalled()
    expect(input).toHaveValue('draft')
  })

  it('limits the length to what the backend accepts', () => {
    const { input } = setup()
    expect(input).toHaveAttribute('maxlength', String(MAX_MESSAGE_CHARS))
  })
})
