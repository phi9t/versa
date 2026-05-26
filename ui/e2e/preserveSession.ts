import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

import {
  E2E_DB,
  E2E_FULL_REVIEW_DIR,
  E2E_FULL_REVIEW_TASK,
  repoRoot,
} from './globalSetup'

function shellQuote(value: string): string {
  return JSON.stringify(value)
}

export function preserveFullCodexSession(): void {
  if (!fs.existsSync(E2E_DB)) {
    console.warn(`[e2e] Skip preserve — database not found: ${E2E_DB}`)
    return
  }

  fs.mkdirSync(E2E_FULL_REVIEW_DIR, { recursive: true })

  const requirementsMd = path.join(E2E_FULL_REVIEW_DIR, 'requirements.md')
  const snapshotJson = path.join(E2E_FULL_REVIEW_DIR, 'snapshot.json')
  const reviewMd = path.join(E2E_FULL_REVIEW_DIR, 'REVIEW.md')
  const dbCopy = path.join(E2E_FULL_REVIEW_DIR, 'state.db')

  execSync(
    `versa export --db ${shellQuote(E2E_DB)} --task-id ${shellQuote(E2E_FULL_REVIEW_TASK)} --format md --output ${shellQuote(requirementsMd)}`,
    { cwd: repoRoot, stdio: 'inherit' },
  )
  execSync(
    `versa state --db ${shellQuote(E2E_DB)} --task-id ${shellQuote(E2E_FULL_REVIEW_TASK)} --format json > ${shellQuote(snapshotJson)}`,
    { cwd: repoRoot, stdio: 'inherit', shell: '/bin/bash' },
  )

  fs.copyFileSync(E2E_DB, dbCopy)
  for (const suffix of ['-wal', '-shm']) {
    const sidecar = `${E2E_DB}${suffix}`
    if (fs.existsSync(sidecar)) {
      fs.copyFileSync(sidecar, `${dbCopy}${suffix}`)
    }
  }

  const review = `# Full Codex E2E session — review

Task ID: \`${E2E_FULL_REVIEW_TASK}\`
SQLite (canonical): \`${E2E_DB}\`

## Artifacts in this folder

| File | Description |
|------|-------------|
| \`requirements.md\` | Synthesized requirements document |
| \`snapshot.json\` | Session snapshot (facts, messages, slots, readiness) |
| \`state.db\` | Copy of the SQLite database at preserve time |

## Reopen in the UI

\`\`\`bash
pip install -e ".[dev,api]"
cd ui && npm run build && cd ..
versa serve --port 8000 --db ${E2E_DB}
\`\`\`

Open http://localhost:8000 and load task ID \`${E2E_FULL_REVIEW_TASK}\`.

## CLI

\`\`\`bash
versa state --db ${E2E_DB} --task-id ${E2E_FULL_REVIEW_TASK} --format json
versa export --db ${E2E_DB} --task-id ${E2E_FULL_REVIEW_TASK} --format md
\`\`\`
`
  fs.writeFileSync(reviewMd, review, 'utf-8')

  console.log(`\n[e2e] Session preserved for review:`)
  console.log(`  ${E2E_FULL_REVIEW_DIR}/`)
  console.log(`  DB: ${E2E_DB}`)
}
