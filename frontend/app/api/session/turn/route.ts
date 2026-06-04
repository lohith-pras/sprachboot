import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const res = await fetch(`${API_URL}/session/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const text = await res.text()
  try {
    const data = JSON.parse(text)
    return NextResponse.json(data, { status: res.status })
  } catch {
    // Backend returned non-JSON (e.g. 500 Internal Server Error)
    return NextResponse.json(
      { error: 'Backend error', detail: text.slice(0, 200) },
      { status: res.status }
    )
  }
}
