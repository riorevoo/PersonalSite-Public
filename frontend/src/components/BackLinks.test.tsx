import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { BackLinks } from './BackLinks'

function setup(toWriting?: boolean) {
  render(
    <MemoryRouter>
      <BackLinks toWriting={toWriting} />
    </MemoryRouter>,
  )
}

describe('BackLinks', () => {
  it('always offers a way back to the conversation', () => {
    setup()

    expect(screen.getByRole('link', { name: '← back to asking' })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: '← all writing' })).not.toBeInTheDocument()
  })

  it('also offers the writing list on a post page, before the way back to asking', () => {
    setup(true)

    const links = screen.getAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual(['← all writing', '← back to asking'])
    expect(links[0]).toHaveAttribute('href', '/writing')
  })

  it('is a labelled navigation region', () => {
    setup()
    expect(screen.getByRole('navigation', { name: 'Back' })).toBeInTheDocument()
  })
})
