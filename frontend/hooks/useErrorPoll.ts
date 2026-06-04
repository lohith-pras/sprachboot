'use client'

import { useCallback, useRef } from 'react'
import { ErrorItem, TurnPollResponse } from '@/lib/types'

interface PollResult {
  errors: ErrorItem[]
  corrected_input: string | null
}

export function useErrorPoll(
  onResult: (msgIndex: number, result: PollResult) => void
) {
  const cancelledRef = useRef<Set<number>>(new Set())

  const poll = useCallback(
    (turnId: number, msgIndex: number) => {
      let attempts = 0
      const MAX = 12

      const tick = async () => {
        if (cancelledRef.current.has(turnId)) return
        attempts++
        try {
          const res = await fetch(`/api/session/${turnId}`)
          const data: TurnPollResponse = await res.json()

          if (data.error_count > 0 || data.corrected_input) {
            onResult(msgIndex, {
              errors: data.errors,
              corrected_input: data.corrected_input,
            })
            cancelledRef.current.delete(turnId)
            return
          }
        } catch { /* silent */ }

        if (attempts < MAX) setTimeout(tick, 1800)
      }

      setTimeout(tick, 1500)
    },
    [onResult]
  )

  const cancel = useCallback((turnId: number) => {
    cancelledRef.current.add(turnId)
  }, [])

  return { poll, cancel }
}
