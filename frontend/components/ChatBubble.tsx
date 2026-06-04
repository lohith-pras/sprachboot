'use client'

import { useState } from 'react'
import { ErrorItem } from '@/lib/types'
import { translateWord, translateSentence } from '@/lib/api'
import ErrorDot from './ErrorDot'

interface Props {
  role: 'user' | 'ai'
  content: string
  errors?: ErrorItem[]
  onErrorClick?: () => void
}

// Split into word and non-word tokens so punctuation/whitespace render unchanged
// while each word stays individually clickable for translation.
function tokenize(text: string): string[] {
  return text.match(/[\p{L}\p{M}ß-]+|[^\p{L}\p{M}ß-]+/gu) ?? [text]
}

const isWord = (t: string) => /[\p{L}]/u.test(t)
const cleanWord = (t: string) => t.replace(/^[-]+|[-]+$/g, '')

export default function ChatBubble({ role, content, errors = [], onErrorClick }: Props) {
  // word-hover tooltip
  const [active, setActive] = useState<number | null>(null)
  const [wordTx, setWordTx] = useState<string | null>(null)
  const [wordLoading, setWordLoading] = useState(false)

  // per-message "show in English"
  const [showEn, setShowEn] = useState(false)
  const [sentenceTx, setSentenceTx] = useState<string | null>(null)
  const [sentenceLoading, setSentenceLoading] = useState(false)

  async function handleWordClick(idx: number, token: string) {
    if (active === idx) {
      setActive(null)
      return
    }
    const word = cleanWord(token)
    setActive(idx)
    setWordTx(null)
    setWordLoading(true)
    const tx = await translateWord(word)
    setWordLoading(false)
    setWordTx(tx ?? 'unavailable')
  }

  async function handleToggleEnglish() {
    if (showEn) {
      setShowEn(false)
      return
    }
    setShowEn(true)
    if (sentenceTx === null) {
      setSentenceLoading(true)
      const tx = await translateSentence(content)
      setSentenceLoading(false)
      setSentenceTx(tx ?? 'Translation unavailable')
    }
  }

  const tokens = tokenize(content)

  return (
    <div className={`bubble-row bubble-row--${role === 'user' ? 'user' : 'ai'}`}>
      <div className={`bubble bubble--${role === 'user' ? 'user' : 'ai'}`}>
        {tokens.map((tok, i) =>
          isWord(tok) ? (
            <span key={i} className="bubble-word" onClick={() => handleWordClick(i, tok)}>
              {tok}
              {active === i && (
                <span className="word-tooltip" onClick={(e) => e.stopPropagation()}>
                  {wordLoading ? '…' : wordTx}
                </span>
              )}
            </span>
          ) : (
            <span key={i}>{tok}</span>
          )
        )}
        {role === 'ai' && showEn && (
          <div className="bubble-translation">
            {sentenceLoading ? 'Translating…' : sentenceTx}
          </div>
        )}
      </div>

      {role === 'ai' && (
        <button type="button" className="translate-toggle" onClick={handleToggleEnglish}>
          {showEn ? 'Hide English' : 'Show in English'}
        </button>
      )}

      {role === 'user' && errors.length > 0 && (
        <ErrorDot count={errors.length} onClick={onErrorClick} />
      )}
    </div>
  )
}
