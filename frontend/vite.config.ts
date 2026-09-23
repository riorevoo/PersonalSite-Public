import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'

// Where the dev server forwards /api calls. The end-to-end tests point this at their own backend.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forward API calls to the FastAPI dev server so the browser sees one origin.
    proxy: {
      '/api': apiTarget,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // Playwright specs live in e2e/ and run with `npm run e2e`, not under Vitest.
    exclude: [...configDefaults.exclude, 'e2e/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/main.tsx',
        'src/**/*.d.ts',
        'src/test/**',
        'src/**/*.test.{ts,tsx}',
        'src/api/types.ts',
      ],
      reporter: [['text', { skipFull: false }], 'html'],
      // Ratchet: raise these when coverage sits 5+ points above; never lower them quietly.
      thresholds: { lines: 85, functions: 85, branches: 85, statements: 85, perFile: true },
    },
  },
})
