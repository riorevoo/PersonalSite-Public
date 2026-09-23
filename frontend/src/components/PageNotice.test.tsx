import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { PageNotice } from './PageNotice'

describe('PageNotice', () => {
  it('shows the message under a page heading, with a way back', () => {
    render(
      <MemoryRouter>
        <PageNotice heading="WRITING">Nothing here.</PageNotice>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
    expect(screen.getByText('Nothing here.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← back to asking' })).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('announces a live message to assistive tech', () => {
    render(
      <MemoryRouter>
        <PageNotice heading="WRITING" live>
          loading…
        </PageNotice>
      </MemoryRouter>,
    )

    expect(screen.getByRole('status')).toHaveTextContent('loading…')
  })

  it('offers the writing list on request', () => {
    render(
      <MemoryRouter>
        <PageNotice heading="WRITING" toWriting>
          Gone.
        </PageNotice>
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: '← all writing' })).toHaveAttribute('href', '/writing')
  })
})
