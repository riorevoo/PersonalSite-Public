import { lazy, useCallback, useRef, useState } from 'react'
import { Route, Routes, useLocation, useMatch, useNavigate } from 'react-router'
import { AboutPopover } from './components/AboutPopover'
import { Composer } from './components/Composer'
import { MessageList } from './components/MessageList'
import { RouteBoundary } from './components/RouteBoundary'
import { Shell } from './components/Shell'
import { SuggestionChips } from './components/SuggestionChips'
import { TopBar } from './components/TopBar'
import { WelcomeHero } from './components/WelcomeHero'
import { profile } from './content/profile'
import { useAutofill } from './hooks/useAutofill'
import { useChat } from './hooks/useChat'
import { NotFoundRoute } from './routes/NotFoundRoute'

const PostRoute = lazy(() => import('./routes/PostRoute').then((m) => ({ default: m.PostRoute })))
const WritingRoute = lazy(() =>
  import('./routes/WritingRoute').then((m) => ({ default: m.WritingRoute })),
)

/** How many of the suggestion chips are offered under a post ("ask about this"). */
const POST_QUESTIONS = 2

function App() {
  // The conversation lives here, above the routes, so it survives a trip to the Writing pages.
  const chat = useChat()
  const navigate = useNavigate()
  const location = useLocation()
  const onChat = useMatch('/') !== null
  const onPost = useMatch('/writing/:slug') !== null
  const [aboutOpen, setAboutOpen] = useState(false)
  const aboutButtonRef = useRef<HTMLButtonElement>(null)
  const started = chat.messages.length > 0

  const ask = (question: string) => {
    setAboutOpen(false)
    chat.ask(question)
  }

  // A chip puts its question in the text box and then sends it, as if it had been typed.
  const composer = useAutofill(ask)
  const busy = chat.pending || composer.filling

  const pickSuggestion = (question: string) => {
    setAboutOpen(false)
    composer.autofill(question)
  }

  const askFromPost = (question: string) => {
    ask(question)
    void navigate('/')
  }

  const reset = () => {
    setAboutOpen(false)
    composer.cancel()
    chat.reset()
  }

  const closeAbout = useCallback((restoreFocus: boolean) => {
    setAboutOpen(false)
    if (restoreFocus) aboutButtonRef.current?.focus()
  }, [])

  return (
    <Shell
      layout={onChat ? 'chat' : 'reading'}
      topBar={
        <TopBar
          name={profile.name}
          started={started}
          nameAsHeading={onChat}
          aboutOpen={aboutOpen}
          aboutButtonRef={aboutButtonRef}
          onReset={reset}
          onToggleAbout={() => (aboutOpen ? closeAbout(true) : setAboutOpen(true))}
          onOpenBlog={() => setAboutOpen(false)}
        />
      }
      overlay={
        aboutOpen ? (
          <AboutPopover profile={profile} triggerRef={aboutButtonRef} onClose={closeAbout} />
        ) : undefined
      }
      footer={
        onChat ? (
          <>
            <SuggestionChips
              suggestions={profile.suggestions}
              disabled={busy}
              onPick={pickSuggestion}
            />
            <Composer
              value={composer.draft}
              onChange={composer.setDraft}
              onSubmit={ask}
              disabled={busy}
              readOnly={composer.filling}
            />
          </>
        ) : undefined
      }
    >
      <RouteBoundary key={location.pathname} heading={profile.writing.heading} toWriting={onPost}>
        <Routes>
          <Route
            path="/"
            element={
              started ? (
                <MessageList messages={chat.messages} onRetry={chat.retry} />
              ) : (
                <WelcomeHero profile={profile} />
              )
            }
          />
          <Route path="/writing" element={<WritingRoute {...profile.writing} />} />
          <Route
            path="/writing/:slug"
            element={
              <PostRoute
                heading={profile.writing.heading}
                questions={profile.suggestions.slice(0, POST_QUESTIONS)}
                onAsk={askFromPost}
              />
            }
          />
          <Route path="*" element={<NotFoundRoute />} />
        </Routes>
      </RouteBoundary>
    </Shell>
  )
}

export default App
