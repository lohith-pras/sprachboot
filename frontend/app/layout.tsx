import type { Metadata } from 'next'
import './globals.css'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'

export const metadata: Metadata = {
  title: 'SprachBoot — Speak German from day one',
  description:
    'SprachBoot is a German conversation partner that talks back, catches your mistakes, and remembers them — so every session is easier than the last. Built for learners and newcomers in Germany.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
        <Footer />
      </body>
    </html>
  )
}
