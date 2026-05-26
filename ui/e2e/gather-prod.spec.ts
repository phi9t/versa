import { expect, test } from '@playwright/test'
import { REQUIREMENTS_OPENING, loadSession, sendChatMessage } from './helpers'

test.describe('Prod stack', () => {
  test('serves SPA at root', async ({ page }) => {
    const response = await page.goto('/')
    expect(response?.status()).toBe(200)
    await expect(page.getByRole('heading', { name: 'Versa Requirements Gatherer' })).toBeVisible()
  })

  test('SPA survives hard reload', async ({ page }) => {
    await loadSession(page, 'e2e-reload')
    await page.reload()
    await expect(page.getByRole('heading', { name: 'Versa Requirements Gatherer' })).toBeVisible()
    await expect(page.getByTestId('chat-messages')).toBeVisible()
  })

  test('health endpoint responds', async ({ request }) => {
    const res = await request.get('/api/health')
    expect(res.ok()).toBeTruthy()
    await expect(res.json()).resolves.toEqual({ ok: true })
  })

  test('codex turn returns assistant reply', async ({ page }) => {
    test.setTimeout(900_000)
    await loadSession(page, 'e2e-codex-turn')
    await sendChatMessage(page, REQUIREMENTS_OPENING)
    await page.getByTestId('tab-facts').click()
    await expect(page.getByRole('heading', { name: 'objective' })).toBeVisible({
      timeout: 120_000,
    })
  })
})
