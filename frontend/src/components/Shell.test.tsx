import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Shell } from './Shell'

describe('Shell', () => {
  it('renders the content inside main and the footer inside contentinfo', () => {
    render(<Shell footer={<span>footer content</span>}>body content</Shell>)

    expect(screen.getByRole('main')).toHaveTextContent('body content')
    expect(screen.getByRole('contentinfo')).toHaveTextContent('footer content')
  })

  it('renders the top bar and overlay only when given', () => {
    const { rerender } = render(<Shell footer={null}>x</Shell>)
    expect(screen.queryByText('top bar')).not.toBeInTheDocument()
    expect(screen.queryByText('overlay')).not.toBeInTheDocument()

    rerender(
      <Shell footer={null} topBar={<span>top bar</span>} overlay={<span>overlay</span>}>
        x
      </Shell>,
    )
    expect(screen.getByText('top bar')).toBeInTheDocument()
    expect(screen.getByText('overlay')).toBeInTheDocument()
  })

  it('keeps the overlay outside the scroll area, so scrolling does not move it', () => {
    render(
      <Shell footer={null} overlay={<span>overlay</span>}>
        <span>body</span>
      </Shell>,
    )

    const main = screen.getByRole('main')
    expect(main).toContainElement(screen.getByText('body'))
    expect(main).not.toContainElement(screen.getByText('overlay'))
  })

  it('leaves out the footer when there is none, as on the reading pages', () => {
    render(<Shell layout="reading">body content</Shell>)

    expect(screen.getByRole('main')).toHaveTextContent('body content')
    expect(screen.queryByRole('contentinfo')).not.toBeInTheDocument()
  })

  it('marks the layout so the reading pages get their own padding', () => {
    const { rerender } = render(<Shell>x</Shell>)
    expect(screen.getByRole('main')).toHaveAttribute('data-layout', 'chat')

    rerender(<Shell layout="reading">x</Shell>)
    expect(screen.getByRole('main')).toHaveAttribute('data-layout', 'reading')
  })

  it('puts the top bar before the scroll area and the footer after it', () => {
    render(
      <Shell footer={<span>footer</span>} topBar={<span>top bar</span>}>
        <span>body</span>
      </Shell>,
    )

    const order = ['top bar', 'body', 'footer'].map((text) => screen.getByText(text))
    order.slice(1).forEach((node, i) => {
      const previous = order[i] as HTMLElement
      expect(previous.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    })
  })
})
