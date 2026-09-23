# Personal Site: Frontend

Vite + React + TypeScript single-page app for the chat-style personal site. Visitors click a
suggestion chip or type a question; answers come from the FastAPI backend (`../backend`).

The visual design is fixed (the design sources are kept offline by the site owner, not in this
repository). All colours/fonts/shadows are tokens in `src/styles/tokens.css`.

## Requirements

- Node.js 20.19+ (or 22.12+) and npm

## Setup & run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Start the backend too (`cd backend && uv run fastapi dev app/main.py`). In dev, Vite proxies
every `/api/*` request to `http://localhost:8000` (see `vite.config.ts`), so no CORS setup is
needed and the client uses relative URLs.

## Scripts

| Command              | What it does                          |
|----------------------|---------------------------------------|
| `npm run dev`        | Dev server with HMR                   |
| `npm run build`      | Type-check (`tsc -b`) + production build to `dist/` |
| `npm run preview`    | Serve the production build locally    |
| `npm run typecheck`  | `tsc -b` type check, no output        |
| `npm run lint`       | oxlint (warnings fail) then Stylelint on `src/**/*.css` |
| `npm run format`     | Prettier, rewrite files               |
| `npm run format:check` | Prettier, check only (used before finishing) |
| `npm test`           | Vitest (jsdom + Testing Library), single run |
| `npm run test:watch` | Vitest in watch mode                  |
| `npm run test:coverage` | Vitest with v8 coverage; fails below the thresholds |
| `npm run types:generate` | Regenerate `src/api/schema.d.ts` from `../backend/openapi.json` |
| `npm run types:check` | Regenerate and fail if `schema.d.ts` differs from what is committed |
| `npm run e2e`        | Playwright end-to-end tests (starts its own backend and frontend) |
| `npm run e2e:update` | Re-record the screenshot baselines after an intended visual change |
| `npm run e2e:report` | Open the last Playwright HTML report |

### End-to-end tests

`e2e/` holds Playwright specs that drive the real app in Chromium against the real backend (with
the placeholder engine and raised rate limits). `playwright.config.ts` starts both servers on
their own ports (API 8100, site 4173), so your dev servers are never touched. One-time setup:
`npx playwright install chromium`.

- `chat.spec.ts`: chips, typing, Enter and SEND, history, start over, the about popover, and the
  error, rate-limit and thinking states.
- `layout.spec.ts`: no sideways scrolling, popover and composer on screen at 360 to 1920 px, the
  1100 px column, short screens.
- `a11y.spec.ts`: axe (WCAG 2 A/AA) on the welcome, chat, popover and error states.
- `mobile.spec.ts`: a phone (touch) run of the main flow.
- `visual.spec.ts` (`@visual`): screenshot baselines of the design. They are recorded on Windows
  (`*-win32.png`) and only run locally; CI skips them. Review any change against the
  design screenshot (kept offline) before `npm run e2e:update`.

A test that passes even when the feature is broken is worse than none: when you add one, break the
behaviour on purpose once and confirm the test fails.

Before a change is done: `format:check`, `lint`, `typecheck`, `test:coverage` and `build` must all
pass. Coverage thresholds (85% lines, functions, branches and statements) apply **per file**, so a
new untested file fails even if the average is fine. They live in `vite.config.ts`; raise them when
coverage sits well above, do not lower them quietly. `@vitest/coverage-v8` must stay on the same
version as `vitest`.

## Configuration

| Variable            | Default | Purpose                                              |
|---------------------|---------|------------------------------------------------------|
| `VITE_API_BASE_URL` | empty   | API origin when not served behind the same host/proxy |

Copy `.env.example` to `.env.local` to override.

## Layout

```
src/
  main.tsx              entry
  App.tsx               composes the page: welcome hero or conversation, chips, composer
  index.css             font imports (@fontsource, self-hosted), global reset, focus ring
  styles/tokens.css     design tokens: colours, fonts, type presets, shadows, dot grid
  styles/utilities.module.css   shared helpers (visually hidden text)
  content/profile.ts    name, tagline, bio, facts, links, suggestion chips (single source)
  constants.ts          MAX_MESSAGE_CHARS (mirrors the backend limit)
  hooks/useChat.ts      conversation state: one request at a time, retry, reset cancels
  api/client.ts         typed fetch wrapper: getHealth(), postChat()
  api/types.ts          friendly names for the generated types
  api/schema.d.ts       GENERATED from backend/openapi.json (do not edit; types:generate)
  components/           one component per file, each with a CSS Module and a test:
                        Shell, WelcomeHero, FactsTable, LinkRow, SuggestionChips, Composer,
                        MessageList, UserBubble, AnswerCard, TopBar, AboutPopover
  test/setup.ts         jest-dom matchers, scrollIntoView stub, cleanup
```

Behaviour: the welcome hero shows until the first question; then the top bar appears (name,
"start over", and the "about me" popover). Enter or SEND submits, a chip click asks its text, and
asking closes the popover. Chips and SEND are inert while an answer is pending (they use
`aria-disabled`, so keyboard focus is not lost). An answer that takes longer than 30 seconds (or a
failed request) shows an error card with a "try again" button. A tall answer is scrolled to its
first line. The layout is capped at the design's 1100px width and centred on wider screens.

Fonts: Chivo (300/400/500/700), Martian Mono (700), Space Mono (400/700).
