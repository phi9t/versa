import { execSync, spawn, type ChildProcess } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const repoRoot = path.join(__dirname, '..', '..')

export const E2E_PORT = process.env.VERSA_E2E_PORT ?? '8765'
export const E2E_RESTART_PORT = String(Number(E2E_PORT) + 1)
function resolveDbPath(raw: string | undefined, defaultRelative: string): string {
  if (!raw) {
    return path.join(repoRoot, defaultRelative)
  }
  if (path.isAbsolute(raw)) {
    return raw
  }
  const normalized = raw.replace(/^\.\.\//, '')
  return path.join(repoRoot, normalized)
}

export const E2E_DB = resolveDbPath(
  process.env.VERSA_E2E_DB,
  path.join('ui', 'e2e', '.test-state.db'),
)
export const E2E_RESTART_DB = resolveDbPath(
  process.env.VERSA_E2E_RESTART_DB,
  path.join('ui', 'e2e', '.restart-test-state.db'),
)
export const E2E_USE_MOCK = process.env.VERSA_E2E_MOCK === '1'
export const E2E_PRESERVE = process.env.VERSA_E2E_PRESERVE === '1'
export const E2E_PRESERVE_RESUME = process.env.VERSA_E2E_PRESERVE_RESUME === '1'
export const E2E_FULL_REVIEW_TASK = 'e2e-full-codex'
export const E2E_FULL_REVIEW_DIR = path.join(repoRoot, '.versa', 'e2e-full-codex-review')
export const E2E_FULL_REVIEW_DB = path.join(repoRoot, '.versa', 'e2e-full-codex-review.db')
export const TURN_TIMEOUT_MS = 120_000

export function serveArgs(port: string = E2E_PORT, dbPath: string = E2E_DB): string[] {
  const args = ['serve', '--port', port, '--db', dbPath]
  if (E2E_USE_MOCK) args.push('--mock')
  return args
}

function shellQuote(value: string): string {
  return JSON.stringify(value)
}

export function serveCommand(port: string = E2E_PORT, dbPath: string = E2E_DB): string {
  const clean = E2E_PRESERVE_RESUME
    ? ''
    : `rm -f ${shellQuote(dbPath)} ${shellQuote(`${dbPath}-wal`)} ${shellQuote(`${dbPath}-shm`)} 2>/dev/null;`
  return `${clean} ${['versa', ...serveArgs(port, dbPath)].join(' ')}`
}

export async function waitForHealth(baseUrl: string, timeoutMs = 60_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  let delayMs = 50
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${baseUrl}/api/health`)
      if (res.ok) return
    } catch {
      // retry until deadline
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs))
    delayMs = Math.min(delayMs * 2, 500)
  }
  throw new Error(`Server not healthy at ${baseUrl} within ${timeoutMs}ms`)
}

export function runVersaDoctor(): void {
  if (E2E_USE_MOCK) return
  execSync('versa doctor', { cwd: repoRoot, stdio: 'inherit' })
}

export async function restartVersaServer(
  port: string = E2E_PORT,
  dbPath: string = E2E_DB,
): Promise<ChildProcess> {
  const child = spawn('versa', serveArgs(port, dbPath), {
    cwd: repoRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true,
  })
  child.unref()
  await waitForHealth(`http://127.0.0.1:${port}`, 120_000)
  return child
}

export async function stopServer(child: ChildProcess): Promise<void> {
  if (!child.pid || child.killed) return
  await new Promise<void>((resolve) => {
    const finish = () => resolve()
    child.once('exit', finish)
    try {
      process.kill(-child.pid!, 'SIGTERM')
    } catch {
      child.kill('SIGTERM')
    }
    setTimeout(finish, 2_000)
  })
}

export default async function globalSetup(): Promise<void> {
  runVersaDoctor()
}
