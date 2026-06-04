import { proxyGet } from '@/lib/backend-proxy'

export async function GET() {
  return proxyGet('/profile/summary')
}
