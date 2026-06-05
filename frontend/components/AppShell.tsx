'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { getPreferences } from '@/lib/settings'
import { isSignedIn } from '@/lib/auth'
import Nav from './Nav'
import Footer from './Footer'

// Routes that render without app chrome and without the onboarding gate.
const PUBLIC_ROUTES = ['/', '/onboard']

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const isPublic = PUBLIC_ROUTES.includes(pathname)
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    if (isPublic) return
    setChecked(false)
    let active = true
    getPreferences()
      .then((p) => {
        if (!active) return
        if (!p.onboarding_complete) {
          router.replace('/onboard')
        } else if (!isSignedIn()) {
          // Onboarded but signed out — send to the landing page to sign in.
          router.replace('/')
        } else {
          setChecked(true)
        }
      })
      .catch(() => {
        // Backend unreachable — render the app rather than trapping the user.
        if (active) setChecked(true)
      })
    return () => {
      active = false
    }
  }, [pathname, isPublic, router])

  // Landing and onboarding bring their own layout; no app chrome, no gate.
  if (isPublic) return <>{children}</>

  // App routes: hold render until the onboarding check resolves (no flash).
  if (!checked) {
    return <div className="app-loading" aria-busy="true" aria-label="Loading" />
  }

  return (
    <>
      <Nav />
      {children}
      <Footer />
    </>
  )
}
