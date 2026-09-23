import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LinkRow } from './LinkRow'

describe('LinkRow', () => {
  it('prefixes each label with an arrow', () => {
    render(<LinkRow links={[{ label: 'github', href: '#' }]} />)
    expect(screen.getByRole('link', { name: '→ github' })).toHaveAttribute('href', '#')
  })

  it('opens external links in a new tab safely', () => {
    render(<LinkRow links={[{ label: 'site', href: 'https://example.com' }]} />)
    const link = screen.getByRole('link', { name: '→ site' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('leaves internal links in the same tab', () => {
    render(<LinkRow links={[{ label: 'resume', href: '/resume.pdf' }]} />)
    const link = screen.getByRole('link', { name: '→ resume' })
    expect(link).not.toHaveAttribute('target')
    expect(link).not.toHaveAttribute('rel')
  })

  it('opens an internal link in a new tab when it asks to, as the resume PDF does', () => {
    render(<LinkRow links={[{ label: 'resume', href: '/api/resume', newTab: true }]} />)
    const link = screen.getByRole('link', { name: '→ resume' })
    expect(link).toHaveAttribute('href', '/api/resume')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('supports start alignment', () => {
    render(<LinkRow links={[{ label: 'a', href: '#' }]} align="start" />)
    expect(screen.getByRole('list').className).toContain('start')
  })
})
