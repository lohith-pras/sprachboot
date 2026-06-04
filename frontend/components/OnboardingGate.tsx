'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { getPreferences } from '@/lib/settings'

export default function OnboardingGate() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (pathname === '/onboard') return
    getPreferences()
      .then((p) => { if (!p.onboarding_complete) router.replace('/onboard') })
      .catch(() => { /* backend down — let app render */ })
  }, [pathname, router])

  return null
}
