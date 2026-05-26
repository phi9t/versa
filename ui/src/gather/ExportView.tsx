import { useState } from 'react'
import { Copy, Download } from 'lucide-react'
import { errorMessage, fetchExport } from '../lib/api'

interface ExportViewProps {
  taskId: string
}

export default function ExportView({ taskId }: ExportViewProps) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadExport = async (format: 'md' | 'json') => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetchExport(taskId, format)
      setContent(response.content)
    } catch (err: unknown) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="export-panel">
      <div className="export-actions">
        <button type="button" disabled={loading} onClick={() => void loadExport('md')}>
          <Download size={16} aria-hidden="true" />
          Load Markdown
        </button>
        <button type="button" disabled={loading} onClick={() => void loadExport('json')}>
          <Download size={16} aria-hidden="true" />
          Load JSON
        </button>
        {content && (
          <button
            type="button"
            onClick={() => void navigator.clipboard.writeText(content)}
          >
            <Copy size={16} aria-hidden="true" />
            Copy
          </button>
        )}
      </div>
      {error && <p className="text-danger">{error}</p>}
      {content && <pre className="export-content" data-testid="export-content">{content}</pre>}
    </div>
  )
}
