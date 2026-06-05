'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function ReviewPage() {
  const [scenarios, setScenarios] = useState<any[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [feedback, setFeedback] = useState<any | null>(null)

  useEffect(() => {
    async function loadDeck() {
      try {
        const res = await fetch(api('/review/deck'))
        const data = await res.json()
        setScenarios(data.scenarios || [])
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    loadDeck()
  }, [])

  if (loading) {
    return (
      <main style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
        <h2>Loading review deck...</h2>
      </main>
    )
  }

  if (scenarios.length === 0) {
    return (
      <main style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
        <h2>No reviews due! 🎉</h2>
        <Link href="/dashboard" className="btn" style={{ marginTop: 'var(--space-md)' }}>Back to Dashboard</Link>
      </main>
    )
  }

  if (currentIndex >= scenarios.length) {
    return (
      <main style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
        <h2>Review Complete! 🎉</h2>
        <Link href="/dashboard" className="btn" style={{ marginTop: 'var(--space-md)' }}>Back to Dashboard</Link>
      </main>
    )
  }

  const currentScenario = scenarios[currentIndex]

  const checkAnswer = async () => {
    if (!input.trim()) return
    setChecking(true)
    setFeedback(null)
    
    try {
      const res = await fetch(api('/review/check'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_prompt: currentScenario.prompt,
          user_response: input.trim()
        })
      })
      const data = await res.json()
      setFeedback(data)
    } catch (e) {
      console.error(e)
    } finally {
      setChecking(false)
    }
  }

  const nextScenario = () => {
    setCurrentIndex(i => i + 1)
    setInput('')
    setFeedback(null)
  }

  return (
    <main>
      <div className="dashboard" style={{ maxWidth: 600, margin: '0 auto', paddingTop: '10vh' }}>
        
        <div style={{ marginBottom: 'var(--space-xl)', display: 'flex', justifyContent: 'space-between' }}>
          <Link href="/dashboard" style={{ color: 'var(--color-ink-2)' }}>← Back</Link>
          <span className="mono-label">Scenario {currentIndex + 1} of {scenarios.length}</span>
        </div>

        <article className="cell tint-paper" style={{ padding: 'var(--space-xl)' }}>
          <span className="mono-label cell__tag">Roleplay</span>
          <h2 style={{ marginTop: 'var(--space-sm)' }}>{currentScenario.prompt}</h2>
          
          <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink-2)' }}>
            Target word: <strong>{currentScenario.target_word}</strong>
          </p>
          
          <div style={{ marginTop: 'var(--space-xl)' }}>
            <textarea
              className="speak-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Your German response..."
              rows={3}
              disabled={checking || feedback != null}
              style={{ width: '100%', marginBottom: 'var(--space-md)' }}
            />
            
            {!feedback ? (
              <button 
                className="btn" 
                onClick={checkAnswer} 
                disabled={checking || !input.trim()}
                style={{ width: '100%' }}
              >
                {checking ? 'Checking...' : 'Check Answer'}
              </button>
            ) : (
              <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-md)', background: 'var(--color-paper-2)', borderRadius: 'var(--radius-card)' }}>
                {feedback.error ? (
                  <>
                    <h4 style={{ color: 'var(--color-accent-3)' }}>Error</h4>
                    <p style={{ margin: 'var(--space-sm) 0' }}>{feedback.error}. Please try again.</p>
                  </>
                ) : feedback.errors && feedback.errors.length > 0 ? (
                  <>
                    <h4 style={{ color: 'var(--color-accent-3)' }}>Not quite right</h4>
                    <p style={{ margin: 'var(--space-sm) 0' }}>{feedback.corrected}</p>
                    <ul style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
                      {feedback.errors.map((err: any, i: number) => (
                        <li key={i} style={{ marginBottom: '4px' }}>
                          <s>{err.user_fragment}</s> → <strong>{err.correct_form}</strong>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <>
                    <h4 style={{ color: 'var(--color-accent)' }}>Perfekt!</h4>
                    <p style={{ margin: 'var(--space-sm) 0' }}>{feedback.corrected || "Gut gemacht!"}</p>
                  </>
                )}
                
                <button 
                  className="btn" 
                  onClick={nextScenario}
                  style={{ width: '100%', marginTop: 'var(--space-md)' }}
                >
                  Next Scenario →
                </button>
              </div>
            )}
          </div>
        </article>

      </div>
    </main>
  )
}
