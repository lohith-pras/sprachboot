'use client'

// The Regelkreis made visible: where the conversation sits relative to the learner's
// skill. 'stretch' = too easy (push), 'hold' = in the flow channel, 'ease' = too hard.
export type FlowBand = 'ease' | 'hold' | 'stretch' | null | undefined

const MAP: Record<string, { pos: number; color: string; label: string }> = {
  stretch: { pos: 18, color: 'var(--color-ink-2)',     label: 'Too easy — pushing you' },
  hold:    { pos: 50, color: 'var(--color-accent-2)',  label: 'In the flow zone' },
  ease:    { pos: 82, color: 'var(--color-accent-3)',  label: 'Too hard — easing off' },
}

export default function FlowDial({ band }: { band: FlowBand }) {
  const cur = band ? MAP[band] : null
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', minWidth: 220 }}>
      <span className="mono-label" style={{ color: 'var(--color-ink-2)' }}>FLOW</span>
      <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 3,
        background: 'linear-gradient(90deg, #cfc8b8 0%, var(--color-accent-2) 50%, var(--color-accent-3) 100%)' }}>
        {cur && (
          <span style={{ position: 'absolute', left: `${cur.pos}%`, top: -4, width: 14, height: 14,
            marginLeft: -7, borderRadius: '50%', background: cur.color,
            border: '2px solid var(--color-paper)', transition: 'left 0.4s ease' }} />
        )}
      </div>
      <span className="mono-label" style={{ color: cur?.color ?? 'var(--color-ink-2)', whiteSpace: 'nowrap' }}>
        {cur ? cur.label : '—'}
      </span>
    </div>
  )
}
