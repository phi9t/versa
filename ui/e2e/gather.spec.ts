import { expect, test } from '@playwright/test'
import { completeRequirementsGatherWorkflow, loadSession } from './helpers'

test.describe('Requirements gather UI', () => {
  test('loads empty session and shows chat tab', async ({ page }) => {
    await loadSession(page, 'e2e-smoke')

    await expect(page.getByTestId('readiness-value')).toHaveText('Gathering')
    await expect(page.getByTestId('tab-chat')).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('chat-messages')).toContainText('No messages yet')
  })

  test('gathers requirements with structured slot messages end-to-end', async ({ page }) => {
    test.setTimeout(900_000)
    await completeRequirementsGatherWorkflow(page, 'e2e-gather-structured', 'structured')
  })
})
