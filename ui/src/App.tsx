import { useState } from 'react'
import { FileText } from 'lucide-react'
import GatherExplorer from './gather/GatherExplorer'

export default function App() {
  const [taskId, setTaskId] = useState('default')
  const [loadedTaskId, setLoadedTaskId] = useState('default')

  return (
    <div className="relative min-h-screen">
      <div className="observatory-bg" aria-hidden="true" />
      <div className="explorer-container">
        <header className="explorer-header">
          <div className="header-title-section">
            <div className="header-title-row">
              <FileText size={28} className="text-primary" aria-hidden="true" />
              <h1>Versa Requirements Gatherer</h1>
            </div>
            <p>
              Interactive requirements gathering with evidence-backed facts and
              verified synthesis.
            </p>
          </div>
          <form
            className="task-id-form"
            onSubmit={(event) => {
              event.preventDefault()
              setLoadedTaskId(taskId.trim() || 'default')
            }}
          >
            <label htmlFor="task-id">Task ID</label>
            <input
              id="task-id"
              value={taskId}
              onChange={(event) => setTaskId(event.target.value)}
              placeholder="billing-api-spec"
            />
            <button type="submit" data-testid="load-session">Load</button>
          </form>
        </header>
        <GatherExplorer key={loadedTaskId} taskId={loadedTaskId} />
      </div>
    </div>
  )
}
