import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { profile } from '../content/profile'
import { WelcomeHero } from './WelcomeHero'

describe('WelcomeHero', () => {
  it('renders the profile copy', () => {
    render(<WelcomeHero profile={profile} />)

    expect(screen.getByText(profile.name)).toBeInTheDocument()
    expect(screen.getByText(profile.tagline)).toBeInTheDocument()
    expect(screen.getByText(profile.bio)).toBeInTheDocument()
    // The note is text with a picture in the middle; its words are the text parts joined up (and
    // with whitespace collapsed, as the page collapses it around the picture).
    const words = profile.askNote
      .filter((part) => typeof part === 'string')
      .join('')
      .replace(/\s+/g, ' ')
    expect(screen.getByText(words, { exact: false })).toBeInTheDocument()
  })

  describe('the mini me picture', () => {
    const note = (): HTMLElement => screen.getByRole('img', { name: 'my mini me' }).parentElement!

    it('sits inside the note, in place of the words "mini me" after "This is my"', () => {
      render(<WelcomeHero profile={profile} />)
      const picture = screen.getByRole('img', { name: 'my mini me' })

      expect(picture.previousSibling?.textContent).toMatch(/This is my\s*$/)
      expect(picture.nextSibling?.textContent).toMatch(/^\.\s*It knows a bit about me/)
      expect(note()).toHaveTextContent('Get to know me. This is my . It knows a bit about me')
    })

    it('is a small picture with a fixed size, so the text does not jump when it loads', () => {
      render(<WelcomeHero profile={profile} />)
      const picture = screen.getByRole('img', { name: 'my mini me' })

      expect(picture).toHaveAttribute('src', '/minime.png')
      expect(picture).toHaveAttribute('width', '32')
      expect(picture).toHaveAttribute('height', '32')
    })

    it('has words for a screen reader', () => {
      render(<WelcomeHero profile={profile} />)

      expect(screen.getByRole('img', { name: 'my mini me' })).toHaveAccessibleName('my mini me')
    })
  })

  it('renders the headline with the highlighted phrase inside it', () => {
    render(<WelcomeHero profile={profile} />)

    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toHaveTextContent(
      `${profile.headline.before}${profile.headline.highlight}${profile.headline.after}`,
    )
    expect(screen.getByText(profile.headline.highlight)).toBeInTheDocument()
  })

  it('lists the facts and links', () => {
    render(<WelcomeHero profile={profile} />)

    expect(screen.getAllByRole('term')).toHaveLength(profile.facts.length)
    expect(screen.getAllByRole('link')).toHaveLength(profile.links.length)
  })

  it('has no photo block: the only picture is the small mini me', () => {
    render(<WelcomeHero profile={profile} />)

    expect(screen.getAllByRole('img')).toHaveLength(1)
    expect(screen.getByRole('img')).toHaveAccessibleName('my mini me')
    expect(screen.queryByText(/photo of me/i)).not.toBeInTheDocument()
  })
})
