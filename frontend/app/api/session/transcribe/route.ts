import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const formData = await req.formData()
  
  const res = await fetch(`${API_URL}/session/transcribe`, {
    method: 'POST',
    body: formData,
  })
  
  const text = await res.text()
  try {
    const data = JSON.parse(text)
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'Backend error', detail: text.slice(0, 200) },
      { status: res.status }
    )
  }
}
