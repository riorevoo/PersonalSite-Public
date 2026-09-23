import { describe, expect, it } from 'vitest'
import { profile } from './profile'

describe('profile links', () => {
  const link = (label: string) => profile.links.find((item) => item.label === label)

  it('sends the github link to a real github page, not to "#"', () => {
    const github = link('github')

    expect(github?.href).toMatch(/^https:\/\/github\.com\/[\w-]+$/)
  })

  it('opens the sample resume PDF, served by the API, in a new tab', () => {
    const resume = link('résumé (pdf)')

    expect(resume?.href).toBe('/api/resume')
    expect(resume?.newTab).toBe(true)
  })

  it('has no link that goes nowhere', () => {
    for (const { href } of profile.links) expect(href).not.toBe('#')
  })
})

describe('the note under the links', () => {
  it('puts the mini me picture where the words "mini me" would go', () => {
    const [before, picture, after] = profile.askNote

    expect(before).toMatch(/This is my $/)
    expect(picture).toEqual({ src: '/minime.png', alt: 'my mini me' })
    expect(after).toMatch(/^\. It knows a bit about me/)
    expect(profile.askNote).toHaveLength(3)
  })
})
