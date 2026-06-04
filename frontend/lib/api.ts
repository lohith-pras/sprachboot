export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** Build an absolute backend URL from a backend path like '/session/turn'. */
export function api(path: string): string {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}
