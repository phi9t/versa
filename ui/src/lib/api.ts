import type { ExportResponse, SessionSnapshot, TurnResponse } from '../gather/types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : 'Unknown error'
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // ignore
    }
    throw new Error(`${detail} (HTTP ${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function fetchSnapshot(taskId: string): Promise<SessionSnapshot> {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(taskId)}`)
  return parseJson<SessionSnapshot>(res)
}

export async function postTurn(
  taskId: string,
  text: string,
): Promise<TurnResponse> {
  const res = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(taskId)}/turns`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    },
  )
  return parseJson<TurnResponse>(res)
}

export async function fetchExport(
  taskId: string,
  format: 'md' | 'json',
): Promise<ExportResponse> {
  const res = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(taskId)}/export?format=${format}`,
  )
  return parseJson<ExportResponse>(res)
}
