import { NextRequest } from 'next/server'
import { proxyGet } from '@/lib/backend-proxy'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ turnId: string }> }
) {
  const { turnId } = await params
  return proxyGet(`/session/turn/${turnId}`)
}
