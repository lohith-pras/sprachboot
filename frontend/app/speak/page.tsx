'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import ChatBubble from '@/components/ChatBubble'
import ErrorOverlay from '@/components/ErrorOverlay'
import LevelBadge from '@/components/LevelBadge'
import { useSessionTimer } from '@/hooks/useSessionTimer'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'
import { useErrorPoll } from '@/hooks/useErrorPoll'
import { Message, ErrorItem, Topic } from '@/lib/types'
import { api } from '@/lib/api'

const TOPICS: { value: Topic; label: string }[] = [
  { value: 'daily_life', label: 'Daily life' },
  { value: 'uni',        label: 'University' },
  { value: 'engineering',label: 'Engineering' },
  { value: 'test',       label: 'Test prep' },
]

const PATTERN_NAMES: Record<string, string> = {
  "V2_violation": "Verb Position (V2)",
  "dativ_after_in": "Wrong Case (in + Dativ)",
  "gender_article_wrong": "Wrong Gender (der/die/das)",
  "verb_final_subordinate": "Verb at End (Subordinate)",
  "accusative_after_durch": "Wrong Case (durch + Accusative)",
  "false_friend_gift": "False Friend (Gift = Poison)",
  "dativ_after_mit": "Wrong Case (mit + Dativ)",
}

const formatPattern = (key: string) =>
  PATTERN_NAMES[key] || key.replace(/_/g, ' ').toUpperCase()

const GREETING: Message = {
  role: 'ai',
  content: 'Hallo! Wie war dein Tag? Erzähl mir etwas auf Deutsch. 😊',
}

export default function SpeakPage() {
  const router = useRouter()
  const [messages, setMessages]       = useState<Message[]>([GREETING])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [sessionId, setSessionId]     = useState<number | null>(null)
  const [topic, setTopic]             = useState<Topic>('daily_life')
  const [overlay, setOverlay]         = useState<{ errors: ErrorItem[]; corrected: string | null } | null>(null)
  const [lastCorrection, setLastCorrection] = useState<{ errors: ErrorItem[]; corrected: string | null } | null>(null)
  const [isSessionSummary, setIsSessionSummary] = useState(false)
  const [correctionOpen, setCorrectionOpen] = useState(true)
  const [level, setLevel]             = useState('A1')

  const inputRef  = useRef<HTMLTextAreaElement>(null)
  const threadRef = useRef<HTMLDivElement>(null)

  const sessionActive = messages.length > 1
  const seconds = useSessionTimer(sessionActive && !isSessionSummary)

  const formatTime = (s: number) => {
    const m = String(Math.floor(s / 60)).padStart(2, '0')
    const sec = String(s % 60).padStart(2, '0')
    return `${m}:${sec}`
  }

  useEffect(() => {
    fetch(api('/profile/summary'))
      .then(res => res.json())
      .then(data => { if (data.current_level) setLevel(data.current_level) })
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight
    }
  }, [messages, loading])

  const onPollResult = useCallback((msgIndex: number, result: { errors: ErrorItem[]; corrected_input: string | null }) => {
    setMessages((prev) => {
      const next = [...prev]
      next[msgIndex] = { ...next[msgIndex], errors: result.errors, corrected_input: result.corrected_input }
      return next
    })
    setLastCorrection({ errors: result.errors, corrected: result.corrected_input })
  }, [])

  const { poll: pollErrors } = useErrorPoll(onPollResult)

  const sendMessage = async (overrideText?: string) => {
    const text = (typeof overrideText === 'string' ? overrideText : input).trim()
    if (!text || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(api('/session/turn'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, user_input: text, mode: 'chat', topic }),
      })
      const data = await res.json()

      if (!res.ok || data.error) {
        setMessages((prev) => [
          ...prev,
          { role: 'ai', content: 'Entschuldigung, etwas ist schiefgelaufen. Versuche es nochmal.' },
        ])
        return
      }

      if (!sessionId) setSessionId(data.session_id)

      setMessages((prev) => {
        const aiMsg: Message = {
          role: 'ai',
          content: data.ai_response,
          turn_id: data.turn_id,
          errors: [],
          corrected_input: null,
        }
        const next = [...prev, aiMsg]
        pollErrors(data.turn_id, next.length - 2)
        return next
      })
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'ai', content: 'Entschuldigung, es gab einen Fehler. Versuche es nochmal.' },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const { isRecording, toggleRecording } = useVoiceRecorder(async (text) => {
    setLoading(false)
    await sendMessage(text)
  })

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const endSession = async () => {
    if (!sessionId) { router.push('/dashboard'); return }
    try {
      await fetch(api('/session/end'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, duration_s: seconds }),
      })
    } catch (e) {
      console.error(e)
    } finally {
      setIsSessionSummary(true)
    }
  }

  if (isSessionSummary) {
    const allErrors = messages.flatMap(m => m.errors || [])
    return (
      <main className="page section">
        <div className="section__head">
          <h1>Session Summary</h1>
          <p>Great job! You practiced for {formatTime(seconds)}.</p>
        </div>

        <div className="bento">
          <article className="cell tint-paper span-2x1">
            <span className="mono-label cell__tag">Corrections Log</span>
            {allErrors.length === 0 ? (
              <p style={{ marginTop: 'var(--space-md)' }}>Flawless! No major corrections were recorded this session.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, marginTop: 'var(--space-md)' }}>
                {allErrors.map((err, i) => (
                  <li key={i} style={{ padding: 'var(--space-md)', background: 'var(--color-paper-2)', borderRadius: '8px', marginBottom: 'var(--space-sm)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="mono-label" style={{ color: err.severity === 'high' ? 'var(--color-accent-3)' : 'var(--color-ink-2)' }}>
                        {formatPattern(err.pattern_key)}
                      </span>
                    </div>
                    <p style={{ marginTop: 'var(--space-xs)', color: 'var(--color-accent-3)', textDecoration: 'line-through' }}>{err.user_fragment}</p>
                    <p style={{ marginTop: '4px', color: 'var(--color-accent-2)' }}>{err.correct_form}</p>
                    {err.rule && <p style={{ marginTop: 'var(--space-sm)', fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>💡 {err.rule}</p>}
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>

        <div style={{ marginTop: 'var(--space-2xl)', textAlign: 'center' }}>
          <button className="btn" onClick={() => router.push('/dashboard')}>Return to Dashboard</button>
        </div>
      </main>
    )
  }

  return (
    <>
      <div className="speak-layout">

        {/* Top bar */}
        <div className="speak-topbar">
          <LevelBadge level={level as any} />

          <select
            className="topic-select"
            value={topic}
            onChange={(e) => setTopic(e.target.value as Topic)}
            aria-label="Conversation topic"
          >
            {TOPICS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>

          <button
            className="btn btn--soft"
            style={{ fontSize: 'var(--text-xs)', padding: '0.3rem 0.75rem' }}
            onClick={() => setCorrectionOpen((o) => !o)}
            type="button"
            aria-label="Toggle correction panel"
          >
            {correctionOpen ? 'Hide corrections' : 'Show corrections'}
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span className="speak-topbar__timer mono-label">{formatTime(seconds)}</span>
            <button
              className="btn"
              style={{ padding: '0.3rem 0.75rem', fontSize: 'var(--text-xs)', backgroundColor: 'var(--color-accent-3)', boxShadow: 'none', transform: 'none' }}
              onClick={endSession}
            >
              End Session
            </button>
          </div>
        </div>

        {/* Main area */}
        <div className="speak-main">

          {/* Chat thread */}
          <div className="speak-thread">
            <div className="bubble-thread" ref={threadRef}>
              {messages.map((msg, i) => (
                <ChatBubble
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  errors={msg.errors}
                  onErrorClick={() =>
                    setOverlay({ errors: msg.errors ?? [], corrected: msg.corrected_input ?? null })
                  }
                />
              ))}

              {loading && (
                <div className="bubble-row bubble-row--ai">
                  <div className="bubble bubble--ai">
                    <div className="typing-dots">
                      <span /><span /><span />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input bar */}
            <div className="speak-input-bar" style={{ paddingBottom: 'var(--space-xl)' }}>
              <textarea
                ref={inputRef}
                id="speak-input"
                className="speak-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Schreib auf Deutsch… (Enter to send, Shift+Enter for new line)"
                rows={1}
                aria-label="Your message in German"
                disabled={loading}
              />
              <button
                id="speak-mic"
                className={`btn ${isRecording ? 'btn--recording' : 'btn--soft'}`}
                onClick={toggleRecording}
                disabled={loading}
                type="button"
                aria-label="Toggle microphone"
                style={{
                  marginRight: 'var(--space-xs)',
                  color: isRecording ? 'var(--color-accent-3)' : 'inherit',
                  borderColor: isRecording ? 'var(--color-accent-3)' : 'inherit',
                }}
              >
                {isRecording ? 'Stop' : 'Mic'}
              </button>
              <button
                id="speak-send"
                className="btn"
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                type="button"
                aria-label="Send message"
              >
                Send
              </button>
            </div>
          </div>

          {/* Correction panel */}
          <aside
            className={`correction-panel${correctionOpen ? '' : ' hidden'}`}
            aria-label="Last correction"
          >
            {lastCorrection ? (
              <>
                <h4>Last correction</h4>
                {lastCorrection.corrected && (
                  <>
                    <span className="mono-label">Corrected</span>
                    <p style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-xs)' }}>
                      <strong>{lastCorrection.corrected}</strong>
                    </p>
                  </>
                )}
                {lastCorrection.errors.slice(0, 3).map((err, i) => (
                  <div key={i}>
                    <div className="fix-row">
                      <s>{err.user_fragment}</s>
                      <span className="correction__arrow">→</span>
                      <b>{err.correct_form}</b>
                    </div>
                    {err.rule && <p className="correction-note">{err.rule}</p>}
                  </div>
                ))}
                {lastCorrection.errors.length > 3 && (
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>
                    +{lastCorrection.errors.length - 3} more — click the red dot to see all
                  </p>
                )}
              </>
            ) : (
              <>
                <h4>Corrections</h4>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
                  Your corrections will appear here after each turn.
                </p>
              </>
            )}
          </aside>
        </div>
      </div>

      {overlay && (
        <ErrorOverlay
          errors={overlay.errors}
          correctedInput={overlay.corrected}
          onClose={() => setOverlay(null)}
        />
      )}
    </>
  )
}
