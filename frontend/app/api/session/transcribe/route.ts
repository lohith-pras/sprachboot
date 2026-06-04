import { NextRequest } from 'next/server'
import { proxyFormData } from '@/lib/backend-proxy'

export async function POST(req: NextRequest) {
  return proxyFormData('/session/transcribe', req)
}
