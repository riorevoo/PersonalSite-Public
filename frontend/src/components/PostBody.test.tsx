import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PostBody } from './PostBody'

const MARKDOWN = `First paragraph with **bold** and a [link](https://example.com).

## A section

- one
- two

> a quote

\`inline\` code and a block:

\`\`\`
const x = 1
\`\`\`
`

describe('PostBody', () => {
  it('renders Markdown as semantic elements', () => {
    render(<PostBody markdown={MARKDOWN} />)

    expect(screen.getByRole('heading', { level: 2, name: 'A section' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'link' })).toHaveAttribute(
      'href',
      'https://example.com',
    )
    expect(screen.getByText('bold').tagName).toBe('STRONG')
    expect(screen.getByText('a quote').closest('blockquote')).not.toBeNull()
    expect(screen.getByText('inline').tagName).toBe('CODE')
    expect(screen.getByText('const x = 1').closest('pre')).not.toBeNull()
  })

  it('shows raw HTML as text instead of running it', () => {
    const { container } = render(
      <PostBody markdown={'Hello <script>alert(1)</script> <img src=x onerror="alert(1)">'} />,
    )

    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    expect(container).toHaveTextContent('<script>alert(1)</script>')
  })

  it('does not turn a javascript: link into a live link', () => {
    render(<PostBody markdown="[click](javascript:alert(1))" />)

    expect(screen.getByText('click').getAttribute('href') ?? '').not.toMatch(/javascript:/i)
  })
})
