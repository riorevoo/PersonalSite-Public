import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const CI = Boolean(process.env.CI)

// Made-up posts (and a draft) for the tests, so no sample content lives in the real knowledge base.
const KNOWLEDGE_DIR = fileURLToPath(new URL('./e2e/fixtures/knowledge', import.meta.url))

// Dedicated ports so the tests never collide with (or accidentally reuse) your dev servers.
const API_PORT = 8100
const WEB_PORT = 4173

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: CI,
  retries: CI ? 2 : 0,
  reporter: CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  // Screenshot baselines are made on the developer's machine; fonts render differently on the
  // Linux CI runner, so the visual specs (tagged @visual) only run locally.
  grepInvert: CI ? /@visual/ : undefined,
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.01, animations: 'disabled' } },
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}`, trace: 'on-first-retry' },
  projects: [
    {
      name: 'desktop',
      testIgnore: /mobile\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 1160, height: 822 } },
    },
    {
      name: 'mobile',
      testMatch: /mobile\.spec\.ts/,
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: [
    {
      // The real API with the placeholder engine, and limits high enough for the whole suite.
      command: `uv run --directory ../backend uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: !CI,
      timeout: 120_000,
      env: {
        APP_ANSWERER: 'stub',
        APP_OWNER_NAME: 'Site Owner',
        APP_KNOWLEDGE_DIR: KNOWLEDGE_DIR,
        APP_RATE_LIMIT_PER_MINUTE: '1000',
        APP_RATE_LIMIT_PER_DAY: '100000',
        APP_LOG_LEVEL: 'WARNING',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: !CI,
      timeout: 120_000,
      env: { VITE_API_PROXY_TARGET: `http://127.0.0.1:${API_PORT}` },
    },
  ],
})
