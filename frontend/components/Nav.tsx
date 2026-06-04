'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`nav${scrolled ? ' scrolled' : ''}`} id="nav">
      <div className="nav__inner">
        <Link className="nav__brand" href="/">
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

      </div>
    </header>
  )
}
