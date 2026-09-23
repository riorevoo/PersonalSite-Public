/**
 * Public fill-in template. Replace this copy with facts you are comfortable publishing.
 */

export interface ProfileFact {
  label: string
  value: string
}
export interface ProfileLink {
  label: string
  href: string
  newTab?: boolean
}

export interface InlineImage {
  src: string
  alt: string
}

export type TextPart = string | InlineImage

export interface Profile {
  name: string
  tagline: string
  shortTagline: string
  headline: { before: string; highlight: string; after: string }
  bio: string
  shortBio: string
  facts: ProfileFact[]
  links: ProfileLink[]
  askNote: TextPart[]
  suggestions: string[]
  writing: { heading: string; intro: string }
}

export const profile: Profile = {
  name: 'Your Name',
  tagline: 'your role · your specialty · your focus',
  shortTagline: 'your role',
  headline: { before: 'A short ', highlight: 'personal headline', after: '.' },
  bio: 'Add a concise introduction here.',
  shortBio: 'Add a short introduction here.',
  facts: [
    { label: 'status', value: 'add your current status' },
    { label: 'stack', value: 'add your main technologies' },
    { label: 'interest', value: 'add a current interest' },
    { label: 'located', value: 'add your location' },
  ],
  links: [
    { label: 'github', href: 'https://github.com/your-username' },
    { label: 'résumé (pdf)', href: '/api/resume', newTab: true },
  ],
  askNote: [
    'Get to know me. This is my ',
    { src: '/minime.png', alt: 'my mini me' },
    ". It knows a bit about me, and it will tell you when it doesn't.",
  ],
  suggestions: [
    'what experience do you have?',
    'what projects have you worked on?',
    'what are you interested in right now?',
  ],
  writing: {
    heading: 'WRITING',
    intro: 'Add an introduction to your writing here.',
  },
}
