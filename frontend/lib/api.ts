export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** Build an absolute backend URL from a backend path like '/session/turn'. */
export function api(path: string): string {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}

/** Translate a single German word to English. Returns null if unavailable (e.g. no DeepL key). */
export async function translateWord(word: string): Promise<string | null> {
  try {
    const r = await fetch(api('/translate/word'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word }),
    })
    if (!r.ok) return null
    return (await r.json()).translation as string
  } catch {
    return null
  }
}

/** Translate a full German sentence to English. Returns null if unavailable. */
export async function translateSentence(text: string): Promise<string | null> {
  try {
    const r = await fetch(api('/translate/sentence'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (!r.ok) return null
    return (await r.json()).translation as string
  } catch {
    return null
  }
}
