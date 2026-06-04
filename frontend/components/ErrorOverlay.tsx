'use client'

import { useEffect } from 'react'
import { ErrorItem } from '@/lib/types'

interface Props {
  errors: ErrorItem[]
  correctedInput?: string | null
  onClose: () => void
}

export default function ErrorOverlay({ errors, correctedInput, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="overlay-backdrop"
      onClick={onClose}
      aria-hidden="true"
    >
      <div
        className="overlay-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Error analysis"
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 'var(--space-md)',
        }}>
          <h3>Corrections</h3>
          <button
            onClick={onClose}
            aria-label="Close"
            type="button"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '1.25rem',
              color: 'var(--color-ink-2)',
              lineHeight: 1,
              padding: '0.25rem',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            ✕
          </button>
        </div>

        {correctedInput && (
          <div style={{
            marginBottom: 'var(--space-md)',
            padding: 'var(--space-sm) var(--space-md)',
            background: 'var(--color-paper-2)',
            borderRadius: 'var(--radius-sm)',
          }}>
            <span className="mono-label" style={{ marginBottom: '4px', display: 'block' }}>
              Corrected sentence
            </span>
            <strong style={{ fontSize: 'var(--text-sm)' }}>{correctedInput}</strong>
          </div>
        )}

        {errors.length === 0 ? (
          <p style={{ color: 'var(--color-ink-2)', fontSize: 'var(--text-sm)' }}>
            No errors found — great sentence! 🎉
          </p>
        ) : (
          errors.map((err, i) => (
            <div key={i} className={`error-item error-item--${err.severity}`}>
              <div className="error-item__badge">
                {err.error_type} · {err.pattern_key} · {err.severity}
              </div>
              <div className="error-item__fix">
                <s>{err.user_fragment}</s>
                <span className="correction__arrow">→</span>
                <b>{err.correct_form}</b>
              </div>
              {err.rule && (
                <p className="error-item__rule">{err.rule}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
