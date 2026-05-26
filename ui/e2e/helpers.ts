import { expect, type Page } from '@playwright/test'
import { TURN_TIMEOUT_MS } from './globalSetup'

export const REQUIREMENTS_OPENING =
  'Gather requirements for backup CLI. Objective: write_requirements_doc. Ask one blocking question at a time. Do not synthesize until I explicitly approve.'

export const REQUIREMENTS_SLOTS: Array<[string, string | string[]]> = [
  ['scope', 'cross-platform CLI backing up ~/Documents to S3'],
  ['target_users', 'individual developers on macOS and Linux'],
  ['functional_requirements', ['incremental sync', 'resume interrupted uploads']],
  ['non_functional_requirements', ['p99 latency under 500ms']],
  ['constraints', ['no PII in logs']],
  ['success_criteria', ['successful restore from any backup point']],
]

export const SYNTHESIS_TRIGGER = 'Proceed with synthesis.'

export async function triggerSynthesis(page: Page): Promise<void> {
  await sendChatMessage(page, slotMessage('synthesis_requested', true))
  await sendChatMessage(page, SYNTHESIS_TRIGGER)
}

export function slotMessage(key: string, value: string | string[]): string {
  if (typeof value === 'string') {
    return `Use ${key}: ${value}`
  }
  return `Use ${key}: ${JSON.stringify(value)}`
}

export async function loadSession(page: Page, taskId: string): Promise<void> {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Versa Requirements Gatherer' })).toBeVisible()
  await page.getByLabel('Task ID').fill(taskId)
  await page.getByTestId('load-session').click()
  await expect(page.getByTestId('chat-messages')).toBeVisible({ timeout: 30_000 })
}

export async function sendChatMessage(page: Page, text: string): Promise<void> {
  await page.getByTestId('tab-chat').click()
  const textarea = page.getByPlaceholder('Describe a requirement or answer a clarification...')
  const send = page.getByTestId('chat-send')

  await expect(textarea).toBeEnabled({ timeout: TURN_TIMEOUT_MS })
  await textarea.fill(text)
  await expect(send).toBeEnabled()

  const turnResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/turns') &&
      response.request().method() === 'POST' &&
      response.status() === 200,
    { timeout: TURN_TIMEOUT_MS },
  )

  await send.click()
  const response = await turnResponse
  const body = (await response.json()) as { assistant_reply: string }
  expect(body.assistant_reply.length).toBeGreaterThan(0)

  if (!(await textarea.isVisible())) {
    await page.getByTestId('tab-chat').click()
  }
  await expect(textarea).toBeEnabled({ timeout: TURN_TIMEOUT_MS })

  if (await page.getByTestId('chat-messages').isVisible()) {
    await expect(page.getByTestId('chat-messages')).toContainText(text)
  }
}

export async function fillRequirementsSlots(page: Page): Promise<void> {
  await sendChatMessage(page, REQUIREMENTS_OPENING)
  for (const [key, value] of REQUIREMENTS_SLOTS) {
    await sendChatMessage(page, slotMessage(key, value))
  }
  await fillMissingContentSlots(page)
}

export async function fillMissingContentSlots(
  page: Page,
  maxRounds = 3,
): Promise<void> {
  for (let round = 0; round < maxRounds; round += 1) {
    await page.getByTestId('tab-slots').click()
    const missingLine = page.locator('.text-muted').filter({ hasText: 'Still missing:' })
    if (!(await missingLine.isVisible())) {
      return
    }
    const missingText = (await missingLine.textContent()) ?? ''
    let resent = false
    for (const [key, value] of REQUIREMENTS_SLOTS) {
      if (missingText.includes(key)) {
        await sendChatMessage(page, slotMessage(key, value))
        resent = true
      }
    }
    if (!resent) {
      return
    }
  }
}
