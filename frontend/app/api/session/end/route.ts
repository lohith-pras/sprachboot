import { NextRequest } from 'next/server'
import { proxyPost } from '@/lib/backend-proxy'

export async function POST(req: NextRequest) {
  return proxyPost('/session/end', req)
}
