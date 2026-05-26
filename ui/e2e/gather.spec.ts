import { expect, test } from '@playwright/test'
import {
  fillRequirementsSlots,
  loadSession,
  triggerSynthesis,
} from './helpers'

test.describe('Requirements gather UI', () => {
  test('loads empty session and shows chat tab', async ({ page }) => {
    await loadSession(page, 'e2e-smoke')

    await expect(page.getByTestId('readiness-value')).toHaveText('Gathering')
    await expect(page.getByTestId('tab-chat')).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('chat-messages')).toContainText('No messages yet')
  })

  test('gathers requirements and synthesizes document end-to-end', async ({ page }) => {
    test.setTimeout(900_000)
    await loadSession(page, 'e2e-gather-flow')

    await fillRequirementsSlots(page)

    await page.getByTestId('tab-slots').click()
    await expect(page.getByTestId('ready-to-synthesize-banner')).toBeVisible({
      timeout: 120_000,
    })
    await expect(page.getByTestId('readiness-value')).toHaveText('Ready to synthesize')

    await page.getByTestId('tab-facts').click()
    await expect(page.getByRole('heading', { name: 'scope' })).toBeVisible()
    await expect(page.locator('.fact-value').filter({ hasText: 'cross-platform CLI backing up' })).toBeVisible()

    await page.getByTestId('tab-chat').click()
    await triggerSynthesis(page)

    await expect(page.getByTestId('readiness-value')).toHaveText('Synthesized', {
      timeout: 300_000,
    })

    await page.getByTestId('tab-document').click()
    const document = page.getByTestId('document-content')
    await expect(document).toBeVisible()
    await expect(document).toContainText('# Overview')
    await expect(document).toContainText('Cross-platform CLI', { ignoreCase: true })

    await page.getByTestId('tab-export').click()
    await page.getByRole('button', { name: 'Load Markdown' }).click()
    await expect(page.getByTestId('export-content')).toContainText('# Overview', {
      timeout: 10_000,
    })
  })
})
