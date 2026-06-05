'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { currentUser, signOut, onAuthChange } from '@/lib/auth'

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)
  const [user, setUser] = useState<string | null>(null)
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    setUser(currentUser())
    return onAuthChange(() => setUser(currentUser()))
  }, [])

  const handleSignOut = () => {
    signOut()
    router.push('/')
  }

  return (
    <header className={`nav${scrolled ? ' scrolled' : ''}`} id="nav">
      <div className="nav__inner">
        <Link className="nav__brand" href="/dashboard">
          <span aria-hidden="true">⛵</span>
          SprachBoot
        </Link>

        <nav className="nav__center" aria-label="Primary">
          <Link
            className={`nav__link${pathname === '/speak' ? ' active' : ''}`}
            href="/speak"
          >
            Practice
          </Link>
          <Link
            className={`nav__link${pathname === '/test' ? ' active' : ''}`}
            href="/test"
          >
            Test
          </Link>
          <Link
            className={`nav__link${pathname === '/analytics' ? ' active' : ''}`}
            href="/analytics"
          >
            Analytics
          </Link>
          <Link
            className={`nav__link${pathname === '/settings' ? ' active' : ''}`}
            href="/settings"
          >
            Settings
          </Link>
        </nav>

        <div className="nav__right">
          {user && <span className="nav__user">{user}</span>}
          <button className="nav__signout" type="button" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      </div>
    </header>
  )
}
