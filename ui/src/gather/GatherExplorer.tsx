import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BarChart3,
  ClipboardList,
  FileText,
  HelpCircle,
  MessageSquare,
  Download,
} from 'lucide-react'
import ChatPanel from './ChatPanel'
import DocumentPreview from './DocumentPreview'
import ExportView from './ExportView'
import FactsPanel from './FactsPanel'
import OpenQuestions from './OpenQuestions'
import SlotProgress from './SlotProgress'
import {
  GATHER_TAB_ORDER,
  errorMessage,
  fetchSnapshot,
  postTurn,
} from './types'
import type { GatherTabId, Readiness, SessionSnapshot } from './types'

interface GatherExplorerProps {
  taskId: string
}

const TAB_LABELS: Record<GatherTabId, string> = {
  chat: 'Chat',
  facts: 'Facts',
  slots: 'Slots',
  questions: 'Questions',
  document: 'Document',
  export: 'Export',
}

const TAB_ICONS = {
  chat: MessageSquare,
  facts: ClipboardList,
  slots: BarChart3,
  questions: HelpCircle,
  document: FileText,
  export: Download,
} as const

function readinessLabel(readiness: Readiness): string {
  if (readiness === 'gathering') return 'Gathering'
  if (readiness === 'ready_to_synthesize') return 'Ready to synthesize'
  return 'Synthesized'
}

export default function GatherExplorer({ taskId }: GatherExplorerProps) {
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<GatherTabId>('chat')

  const loadSnapshot = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await fetchSnapshot(taskId)
      setSnapshot(data)
    } catch (err: unknown) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    void loadSnapshot()
  }, [loadSnapshot])

  const handleSendTurn = useCallback(
    async (text: string) => {
      try {
        setSending(true)
        setError(null)
        const response = await postTurn(taskId, text)
        setSnapshot(response.snapshot)
        if (response.snapshot.readiness === 'synthesized') {
          setActiveTab('document')
        }
      } catch (err: unknown) {
        setError(errorMessage(err))
      } finally {
        setSending(false)
      }
    },
    [taskId],
  )

  const headerMetrics = useMemo(() => {
    if (!snapshot) return { filled: 0, total: 0, facts: 0, readiness: 'gathering' as Readiness }
    const filled = snapshot.slots.filter((slot) => slot.filled).length
    return {
      filled,
      total: snapshot.slots.length,
      facts: snapshot.facts.length,
      readiness: snapshot.readiness,
    }
  }, [snapshot])

  if (loading) {
    return (
      <div className="loading-container" role="status">
        <div className="spinner" aria-hidden="true" />
        <p>Loading session...</p>
      </div>
    )
  }

  if (error && !snapshot) {
    return (
      <div className="loading-container" role="alert">
        <p>{error}</p>
        <button type="button" onClick={() => void loadSnapshot()}>
          Retry
        </button>
      </div>
    )
  }

  if (!snapshot) {
    return null
  }

  return (
    <>
      {error && <div className="error-banner" role="alert">{error}</div>}

      <div className="gather-stats-row global-stats">
        <div className="stat-chip" data-testid="readiness-chip">
          <span>Readiness:</span>
          <span className="stat-value" data-testid="readiness-value">
            {readinessLabel(headerMetrics.readiness)}
          </span>
        </div>
        <div className="stat-chip">
          <span>Slots:</span>
          <span className="stat-value">
            {headerMetrics.filled}/{headerMetrics.total}
          </span>
        </div>
        <div className="stat-chip">
          <span>Facts:</span>
          <span className="stat-value">{headerMetrics.facts}</span>
        </div>
      </div>

      <section className="gather-main-panel card-view" aria-label="Requirements views">
        <div className="tab-row" role="tablist">
          {GATHER_TAB_ORDER.map((tabId) => {
            const Icon = TAB_ICONS[tabId]
            return (
              <button
                key={tabId}
                type="button"
                role="tab"
                data-testid={`tab-${tabId}`}
                aria-selected={activeTab === tabId}
                className={`tab-button ${activeTab === tabId ? 'active' : ''}`}
                onClick={() => setActiveTab(tabId)}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{TAB_LABELS[tabId]}</span>
              </button>
            )
          })}
        </div>

        <div className="tab-panel tab-panel-active">
          {activeTab === 'chat' && (
            <ChatPanel
              messages={snapshot.messages}
              onSend={handleSendTurn}
              pending={sending}
              readiness={snapshot.readiness}
            />
          )}
          {activeTab === 'facts' && <FactsPanel facts={snapshot.facts} />}
          {activeTab === 'slots' && (
            <SlotProgress
              slots={snapshot.slots}
              readiness={snapshot.readiness}
              missingSlotKeys={snapshot.missing_slot_keys}
            />
          )}
          {activeTab === 'questions' && (
            <OpenQuestions questions={snapshot.open_questions} />
          )}
          {activeTab === 'document' && (
            <DocumentPreview
              content={snapshot.active_artifact}
              status={snapshot.artifact_status}
            />
          )}
          {activeTab === 'export' && <ExportView taskId={taskId} />}
        </div>
      </section>
    </>
  )
}
