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

/** Plain-language answers in slot order (scope first; objective is set by the gather server). */
export const CONVERSATIONAL_REQUIREMENT_ANSWERS = [
  'We are building a cross-platform CLI that backs up ~/Documents to S3.',
  'Individual developers on macOS and Linux.',
  'It must support incremental sync and resume interrupted uploads.',
  'p99 latency should be under 500ms.',
  'No PII in logs.',
  'Successful restore from any backup point.',
]

export const EXPECTED_DOCUMENT_SECTIONS = [
  '# Overview',
  '# Target Users',
  '# Functional Requirements',
  '# Non-Functional Requirements',
  '# Constraints',
  '# Success Criteria',
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

export async function gatherRequirementsConversationally(
  page: Page,
  answers: string[] = CONVERSATIONAL_REQUIREMENT_ANSWERS,
): Promise<void> {
  for (const answer of answers) {
    await sendChatMessage(page, answer)
  }
  await fillMissingContentSlots(page, 5)
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

export async function waitForReadyToSynthesize(page: Page): Promise<void> {
  await page.getByTestId('tab-slots').click()
  await expect(page.getByTestId('ready-to-synthesize-banner')).toBeVisible({
    timeout: 120_000,
  })
  await expect(page.getByTestId('readiness-value')).toHaveText('Ready to synthesize')
}

export async function assertSynthesizedDeliverables(page: Page): Promise<void> {
  await expect(page.getByTestId('readiness-value')).toHaveText('Synthesized', {
    timeout: 300_000,
  })

  await page.getByTestId('tab-facts').click()
  await expect(page.getByRole('heading', { name: 'scope' })).toBeVisible()
  await expect(page.locator('.fact-value').filter({ hasText: 'cross-platform CLI' })).toBeVisible()

  await page.getByTestId('tab-document').click()
  const document = page.getByTestId('document-content')
  await expect(document).toBeVisible()
  for (const section of EXPECTED_DOCUMENT_SECTIONS) {
    await expect(document).toContainText(section)
  }
  await expect(document).toContainText('Cross-platform CLI', { ignoreCase: true })
  await expect(document).toContainText('S3', { ignoreCase: true })

  await page.getByTestId('tab-export').click()
  await page.getByRole('button', { name: 'Load Markdown' }).click()
  const exportContent = page.getByTestId('export-content')
  await expect(exportContent).toContainText('# Overview', { timeout: 10_000 })
  for (const section of EXPECTED_DOCUMENT_SECTIONS) {
    await expect(exportContent).toContainText(section)
  }
}

export type GatherMode = 'conversational' | 'structured'

export async function completeRequirementsGatherWorkflow(
  page: Page,
  taskId: string,
  mode: GatherMode = 'conversational',
): Promise<void> {
  await loadSession(page, taskId)

  if (mode === 'conversational') {
    await gatherRequirementsConversationally(page)
  } else {
    await fillRequirementsSlots(page)
  }

  await waitForReadyToSynthesize(page)
  await page.getByTestId('tab-chat').click()
  await triggerSynthesis(page)
  await assertSynthesizedDeliverables(page)
}
