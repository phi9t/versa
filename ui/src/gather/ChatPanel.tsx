import { useState } from 'react'
import { Send } from 'lucide-react'
import type { MessageView, Readiness } from './types'

interface ChatPanelProps {
  messages: MessageView[]
  onSend: (text: string) => Promise<void>
  pending: boolean
  readiness: Readiness
}

export default function ChatPanel({
  messages,
  onSend,
  pending,
  readiness,
}: ChatPanelProps) {
  const [draft, setDraft] = useState('')

  return (
    <div className="chat-panel">
      <div className="chat-hint">
        {readiness === 'ready_to_synthesize'
          ? 'All content slots filled. Say "Proceed with synthesis" when ready.'
          : 'Answer one requirement at a time. Use: Use scope: your answer'}
      </div>
      <div className="chat-messages" role="log" aria-live="polite" data-testid="chat-messages">
        {messages.length === 0 && (
          <p className="text-muted">No messages yet. Start gathering requirements.</p>
        )}
        {messages.map((message) => (
          <div key={message.id} className={`chat-message chat-${message.role}`}>
            <div className="chat-role">{message.role}</div>
            <pre className="chat-content">{message.content}</pre>
          </div>
        ))}
      </div>
      <form
        className="chat-input-row"
        onSubmit={(event) => {
          event.preventDefault()
          const text = draft.trim()
          if (!text || pending) return
          void onSend(text).then(() => setDraft(''))
        }}
      >
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Describe a requirement or answer a clarification..."
          rows={3}
          disabled={pending}
        />
        <button type="submit" disabled={pending || !draft.trim()} data-testid="chat-send">
          <Send size={16} aria-hidden="true" />
          Send
        </button>
      </form>
    </div>
  )
}
