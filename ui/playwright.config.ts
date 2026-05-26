import { defineConfig, devices } from '@playwright/test'
import { E2E_DB, E2E_PORT, repoRoot, serveCommand } from './e2e/globalSetup'

const apiPort = E2E_PORT
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${apiPort}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  globalSetup: './e2e/globalSetup.ts',
  timeout: 900_000,
  use: {
    baseURL,
    trace: 'on-first-retry',
    actionTimeout: 120_000,
  },
  projects: [
    {
      name: 'chromium',
      testIgnore: '**/gather-restart.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'restart',
      testMatch: '**/gather-restart.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: serveCommand(apiPort, E2E_DB),
    cwd: repoRoot,
    url: `${baseURL}/api/health`,
    reuseExistingServer: false,
    timeout: 180_000,
  },
})
