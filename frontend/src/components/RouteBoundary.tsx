import { Component, Suspense, type ReactNode } from 'react'
import { PageNotice } from './PageNotice'

interface RouteBoundaryProps {
  heading: string
  toWriting: boolean
  children: ReactNode
}

/** Keeps navigation available while a route loads or a downloaded module fails. */
export class RouteBoundary extends Component<RouteBoundaryProps, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    const { heading, toWriting, children } = this.props
    if (this.state.failed) {
      return (
        <PageNotice heading={heading} toWriting={toWriting}>
          I could not load this page just now. <a href={window.location.href}>Reload the page</a> to
          try again.
        </PageNotice>
      )
    }
    return (
      <Suspense
        fallback={
          <PageNotice heading={heading} toWriting={toWriting} live>
            loading…
          </PageNotice>
        }
      >
        {children}
      </Suspense>
    )
  }
}
