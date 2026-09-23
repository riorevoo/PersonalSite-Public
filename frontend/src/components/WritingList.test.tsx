import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { summary } from '../test/posts'
import { WritingList } from './WritingList'

function setup(posts = [summary()]) {
  render(
    <MemoryRouter>
      <WritingList heading="WRITING" intro="What I write." posts={posts} />
    </MemoryRouter>,
  )
}

describe('WritingList', () => {
  it('shows the heading, the intro and a way back', () => {
    setup()

    expect(screen.getByRole('heading', { level: 1, name: 'WRITING' })).toBeInTheDocument()
    expect(screen.getByText('What I write.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← back to asking' })).toBeInTheDocument()
  })

  it('lists each post with its summary, tag, date and reading time', () => {
    setup([
      summary({ slug: 'newer', title: 'Newer post', tag: 'postgres', date: '2026-08-14' }),
      summary({ slug: 'older', title: 'Older post', read_minutes: 12, date: '2026-05-01' }),
    ])

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)

    const first = within(items[0] as HTMLElement)
    expect(first.getByRole('heading', { level: 2, name: 'Newer post' })).toBeInTheDocument()
    expect(first.getByText('One sentence about the post.')).toBeInTheDocument()
    expect(first.getByText('postgres')).toBeInTheDocument()
    expect(first.getByText('2026 · 08 · 14')).toHaveAttribute('datetime', '2026-08-14')
    expect(first.getByText('9 min')).toBeInTheDocument()
    expect(within(items[1] as HTMLElement).getByText('12 min')).toBeInTheDocument()
  })

  it('links each title to its post', () => {
    setup([summary({ slug: 'the-slug', title: 'The title' })])

    expect(screen.getByRole('link', { name: 'The title' })).toHaveAttribute(
      'href',
      '/writing/the-slug',
    )
  })

  it('marks a draft', () => {
    setup([summary({ draft: true, tag: 'notes' })])
    expect(screen.getByText('draft · notes')).toBeInTheDocument()
  })

  it('says so when nothing is published yet', () => {
    setup([])

    expect(screen.getByText('Nothing published yet.')).toBeInTheDocument()
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })
})
