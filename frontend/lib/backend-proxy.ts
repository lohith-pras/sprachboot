import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export function backendUrl(path: string): string {
  return `${API_URL}${path}`
}

async function parseResponse(res: Response): Promise<NextResponse> {
  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'Backend error', detail: text.slice(0, 200) },
      { status: res.status }
    )
  }
}

export async function proxyGet(path: string): Promise<NextResponse> {
  try {
    const res = await fetch(backendUrl(path))
    return parseResponse(res)
  } catch {
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 })
  }
}

export async function proxyPost(path: string, req: NextRequest): Promise<NextResponse> {
  try {
    const body = await req.json()
    const res = await fetch(backendUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return parseResponse(res)
  } catch {
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 })
  }
}

export async function proxyFormData(path: string, req: NextRequest): Promise<NextResponse> {
  try {
    const formData = await req.formData()
    const res = await fetch(backendUrl(path), { method: 'POST', body: formData })
    return parseResponse(res)
  } catch {
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 })
  }
}
