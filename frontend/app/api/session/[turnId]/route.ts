import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ turnId: string }> }
) {
  const { turnId } = await params
  const res = await fetch(`${API_URL}/session/turn/${turnId}`)
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
