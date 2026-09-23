import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { UserBubble } from './UserBubble'

describe('UserBubble', () => {
  it('shows the question text', () => {
    render(<UserBubble text="what do you build?" />)
    expect(screen.getByText('what do you build?')).toBeInTheDocument()
  })

  it('renders text literally, not as markup', () => {
    render(<UserBubble text="<b>not bold</b>" />)
    expect(screen.getByText('<b>not bold</b>')).toBeInTheDocument()
  })
})
