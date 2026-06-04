'use client'

import { useState, useRef } from 'react'
import { api } from '@/lib/api'

export function useVoiceRecorder(onTranscribed: (text: string) => void) {
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      setIsRecording(false)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('audio', audioBlob, 'recording.webm')

        try {
          const res = await fetch(api('/session/transcribe'), { method: 'POST', body: formData })
          const data = await res.json()
          if (data.text) onTranscribed(data.text)
        } catch (e) {
          console.error('Transcription error', e)
        } finally {
          stream.getTracks().forEach((track) => track.stop())
        }
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Error accessing microphone', err)
      alert('Could not access microphone.')
    }
  }

  return { isRecording, toggleRecording }
}
