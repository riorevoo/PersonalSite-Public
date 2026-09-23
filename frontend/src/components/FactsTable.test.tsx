import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FactsTable } from './FactsTable'

describe('FactsTable', () => {
  it('renders each fact as a label and value pair', () => {
    render(
      <FactsTable
        facts={[
          { label: 'status', value: 'open to offers' },
          { label: 'stack', value: 'python' },
        ]}
      />,
    )

    expect(screen.getByText('status')).toBeInTheDocument()
    expect(screen.getByText('open to offers')).toBeInTheDocument()
    expect(screen.getByText('stack')).toBeInTheDocument()
    expect(screen.getByText('python')).toBeInTheDocument()
    expect(screen.getAllByRole('term')).toHaveLength(2)
  })

  it('renders an empty list without rows', () => {
    render(<FactsTable facts={[]} />)
    expect(screen.queryAllByRole('term')).toHaveLength(0)
  })
})
