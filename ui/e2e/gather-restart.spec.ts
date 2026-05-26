import { expect, test } from '@playwright/test'
import type { ChildProcess } from 'node:child_process'
import {
  E2E_RESTART_DB,
  E2E_RESTART_PORT,
  restartVersaServer,
  stopServer,
} from './globalSetup'
import {
  REQUIREMENTS_OPENING,
  loadSession,
  sendChatMessage,
  slotMessage,
} from './helpers'

const RESTART_BASE = `http://127.0.0.1:${E2E_RESTART_PORT}`

test.describe.configure({ mode: 'serial' })

let server: ChildProcess

test.beforeAll(async () => {
  server = await restartVersaServer(E2E_RESTART_PORT, E2E_RESTART_DB)
})

test.afterAll(async () => {
  await stopServer(server)
})

test.use({ baseURL: RESTART_BASE })

test('sqlite session survives server restart', async ({ page }) => {
  test.setTimeout(900_000)
  const taskId = 'e2e-restart-persist'
  const scopeValue = 'persistent scope for restart e2e'

  await loadSession(page, taskId)
  await sendChatMessage(page, REQUIREMENTS_OPENING)
  await sendChatMessage(page, slotMessage('scope', scopeValue))

  await page.getByTestId('tab-facts').click()
  await expect(page.locator('.fact-value').filter({ hasText: scopeValue })).toBeVisible({
    timeout: 30_000,
  })

  await stopServer(server)
  server = await restartVersaServer(E2E_RESTART_PORT, E2E_RESTART_DB)

  await loadSession(page, taskId)
  await page.getByTestId('tab-facts').click()
  await expect(page.locator('.fact-value').filter({ hasText: scopeValue })).toBeVisible({
    timeout: 30_000,
  })
})
