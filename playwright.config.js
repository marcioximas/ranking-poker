import { defineConfig, devices } from '@playwright/test'

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Ximas2026@'

export default defineConfig({
  testDir: './tests/ui',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/health',
      env: {
        ...process.env,
        ADMIN_PASSWORD,
      },
      reuseExistingServer: true,
      timeout: 15_000,
    },
    {
      command: 'cd frontend && npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 15_000,
    },
  ],
})
