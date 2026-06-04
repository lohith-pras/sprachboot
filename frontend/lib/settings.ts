const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Preferences {
  user_name: string
  conv_model: string
  analysis_model: string
  onboarding_complete: boolean
}

export interface KeyStatus {
  openrouter: boolean
  openai: boolean
  deepl: boolean
}

export interface ModelOption {
  id: string
  name: string
}

export async function getPreferences(): Promise<Preferences> {
  const r = await fetch(`${API}/settings/preferences`, { cache: 'no-store' })
  if (!r.ok) throw new Error('Failed to load preferences')
  return r.json()
}

export async function updatePreferences(p: Partial<Preferences>): Promise<Preferences> {
  const r = await fetch(`${API}/settings/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p),
  })
  if (!r.ok) throw new Error('Failed to save preferences')
  return r.json()
}

export async function setApiKey(service: string, key: string): Promise<void> {
  const r = await fetch(`${API}/settings/apikey`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, key }),
  })
  if (!r.ok) throw new Error('Failed to save key')
}

export async function getKeyStatus(): Promise<KeyStatus> {
  const r = await fetch(`${API}/settings/apikey/status`, { cache: 'no-store' })
  if (!r.ok) throw new Error('Failed to load key status')
  return r.json()
}

export async function testApiKey(service: string): Promise<{ ok: boolean; detail?: string }> {
  const r = await fetch(`${API}/settings/apikey/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service }),
  })
  return r.json()
}

export async function getModels(): Promise<ModelOption[]> {
  const r = await fetch(`${API}/settings/models`, { cache: 'no-store' })
  if (!r.ok) return []
  return (await r.json()).models
}
