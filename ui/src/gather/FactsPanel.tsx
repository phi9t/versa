import type { FactView } from './types'

interface FactsPanelProps {
  facts: FactView[]
}

export default function FactsPanel({ facts }: FactsPanelProps) {
  if (facts.length === 0) {
    return <p className="text-muted">No facts captured yet.</p>
  }

  return (
    <div className="facts-grid">
      {facts.map((fact) => (
        <article key={fact.id} className="fact-card">
          <header>
            <span className="fact-kind">{fact.kind}</span>
            <h3>{fact.key}</h3>
          </header>
          <pre className="fact-value">{JSON.stringify(fact.value, null, 2)}</pre>
          <blockquote className="fact-evidence">
            Evidence: {fact.evidence_quote}
          </blockquote>
        </article>
      ))}
    </div>
  )
}
