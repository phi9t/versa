interface DocumentPreviewProps {
  content: string | null
  status: 'none' | 'draft' | 'verified' | 'failed' | null
}

export default function DocumentPreview({ content, status }: DocumentPreviewProps) {
  if (!content) {
    return (
      <p className="text-muted">
        No verified document yet. Complete slots and trigger synthesis from Chat.
      </p>
    )
  }

  return (
    <div className="document-preview">
      <div className="document-status">Status: {status ?? 'none'}</div>
      <pre className="document-content" data-testid="document-content">{content}</pre>
    </div>
  )
}
