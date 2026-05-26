import { test } from '@playwright/test'
import {
  E2E_FULL_REVIEW_TASK,
  E2E_PRESERVE,
  E2E_USE_MOCK,
} from './globalSetup'
import { completeRequirementsGatherWorkflow } from './helpers'
import { preserveFullCodexSession } from './preserveSession'

test.describe('Full requirements workflow', () => {
  test('gathers conversationally, synthesizes document, and exports markdown', async ({ page }) => {
    test.setTimeout(900_000)
    const taskId = E2E_PRESERVE
      ? E2E_FULL_REVIEW_TASK
      : E2E_USE_MOCK
        ? 'e2e-full-mock'
        : 'e2e-full-codex'

    try {
      await completeRequirementsGatherWorkflow(page, taskId, 'conversational')
    } finally {
      if (E2E_PRESERVE && !E2E_USE_MOCK) {
        preserveFullCodexSession()
      }
    }
  })
})
