import type { Readiness, SlotStatus } from './types'

interface SlotProgressProps {
  slots: SlotStatus[]
  readiness: Readiness
  missingSlotKeys: string[]
}

export default function SlotProgress({
  slots,
  readiness,
  missingSlotKeys,
}: SlotProgressProps) {
  const filledCount = slots.filter((slot) => slot.filled).length

  return (
    <div className="slots-panel">
      {readiness === 'ready_to_synthesize' && (
        <div className="ready-banner" role="status" data-testid="ready-to-synthesize-banner">
          Ready to synthesize — send &quot;Proceed with synthesis&quot; in Chat.
        </div>
      )}
      <div className="progress-summary">
        {filledCount}/{slots.length} slots filled
      </div>
      <ul className="slot-list">
        {slots.map((slot) => (
          <li key={slot.key} className={slot.filled ? 'slot-filled' : 'slot-missing'}>
            <div className="slot-row">
              <span className="slot-check">{slot.filled ? '✓' : '○'}</span>
              <div>
                <strong>{slot.label}</strong>
                <div className="slot-key">{slot.key}</div>
                {slot.value_preview && (
                  <div className="slot-preview">{slot.value_preview}</div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {missingSlotKeys.length > 0 && (
        <p className="text-muted">Still missing: {missingSlotKeys.join(', ')}</p>
      )}
    </div>
  )
}
