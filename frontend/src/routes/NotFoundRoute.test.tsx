import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { NotFoundRoute } from './NotFoundRoute'

describe('NotFoundRoute', () => {
  it('says there is nothing here, under its own heading, and offers a way back', () => {
    render(
      <MemoryRouter>
        <NotFoundRoute />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'NOT FOUND' })).toBeInTheDocument()
    expect(screen.getByText('There is nothing at this address.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← back to asking' })).toBeInTheDocument()
  })
})
