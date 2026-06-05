// Lightweight local "session" — no password, single-machine. Presence of a
// stored name means the user is signed in. Used to gate app routes and to drive
// the landing Sign-in / Nav Sign-out buttons.

const KEY = 'sb_session'
const EVENT = 'sb-auth-change'

export function currentUser(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(KEY)
}

export function isSignedIn(): boolean {
  return currentUser() !== null
}

export function signIn(name: string): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(KEY, name || 'User')
  window.dispatchEvent(new Event(EVENT))
}

export function signOut(): void {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(KEY)
  window.dispatchEvent(new Event(EVENT))
}

/** Subscribe to sign-in/out changes (same tab + other tabs). Returns unsubscribe. */
export function onAuthChange(cb: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  const onStorage = (e: StorageEvent) => {
    if (e.key === KEY) cb()
  }
  window.addEventListener(EVENT, cb)
  window.addEventListener('storage', onStorage)
  return () => {
    window.removeEventListener(EVENT, cb)
    window.removeEventListener('storage', onStorage)
  }
}
