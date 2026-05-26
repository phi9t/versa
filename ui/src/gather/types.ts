export type Readiness = 'gathering' | 'ready_to_synthesize' | 'synthesized'

export interface MessageView {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface FactView {
  id: string
  kind: string
  key: string
  value: unknown
  evidence_quote: string
  message_id: string
}

export interface SlotStatus {
  key: string
  label: string
  filled: boolean
  value_preview: string | null
}

export interface SessionSnapshot {
  task_id: string
  version: number
  objective: string | null
  facts: FactView[]
  messages: MessageView[]
  open_questions: string[]
  slots: SlotStatus[]
  missing_slot_keys: string[]
  readiness: Readiness
  active_artifact: string | null
  artifact_status: 'none' | 'draft' | 'verified' | 'failed' | null
}

export interface TurnResponse {
  snapshot: SessionSnapshot
  assistant_reply: string
}

export interface ExportResponse {
  format: 'md' | 'json'
  content: string
}

export type GatherTabId =
  | 'chat'
  | 'facts'
  | 'slots'
  | 'questions'
  | 'document'
  | 'export'

export const GATHER_TAB_ORDER: GatherTabId[] = [
  'chat',
  'facts',
  'slots',
  'questions',
  'document',
  'export',
]

export { errorMessage, fetchExport, fetchSnapshot, postTurn } from '../lib/api'
