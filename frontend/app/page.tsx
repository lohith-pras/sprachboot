'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { getPreferences } from '@/lib/settings'
import { signIn } from '@/lib/auth'
import './landing.css'

export default function Landing() {
  const root = useRef<HTMLDivElement>(null)
  const router = useRouter()

  // Enter the app: sign in if onboarded, otherwise start onboarding.
  const enter = async () => {
    try {
      const p = await getPreferences()
      if (p.onboarding_complete) {
        signIn(p.user_name)
        router.push('/dashboard')
        return
      }
    } catch {
      /* backend down — fall through to onboarding */
    }
    router.push('/onboard')
  }

  useEffect(() => {
    const el = root.current
    if (!el) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const cleanups: Array<() => void> = []

    // Nav frost on scroll (rAF-throttled)
    const nav = el.querySelector<HTMLElement>('[data-nav]')
    if (nav) {
      let ticking = false
      const onScroll = () => {
        if (ticking) return
        ticking = true
        requestAnimationFrame(() => {
          nav.classList.toggle('is-scrolled', window.scrollY > 24)
          ticking = false
        })
      }
      window.addEventListener('scroll', onScroll, { passive: true })
      onScroll()
      cleanups.push(() => window.removeEventListener('scroll', onScroll))
    }

    // Reveal-on-enter
    const reveals = Array.from(el.querySelectorAll<HTMLElement>('.reveal'))
    if (reduceMotion || !('IntersectionObserver' in window)) {
      reveals.forEach((r) => r.classList.add('is-in'))
    } else {
      const revObs = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add('is-in')
              revObs.unobserve(e.target)
            }
          })
        },
        { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
      )
      reveals.forEach((r) => revObs.observe(r))
      cleanups.push(() => revObs.disconnect())
    }

    // Counter tick-up
    const counters = Array.from(el.querySelectorAll<HTMLElement>('[data-count-to]'))
    const runCount = (node: HTMLElement) => {
      const target = parseInt(node.getAttribute('data-count-to') || '0', 10) || 0
      if (reduceMotion) {
        node.textContent = String(target)
        return
      }
      const start = performance.now()
      const dur = 1200
      const frame = (now: number) => {
        const t = Math.min((now - start) / dur, 1)
        const eased = 1 - Math.pow(1 - t, 3)
        node.textContent = String(Math.round(eased * target))
        if (t < 1) {
          requestAnimationFrame(frame)
        } else {
          node.textContent = String(target)
          const box = node.closest('.plan__counter') as HTMLElement | null
          box?.animate(
            [{ transform: 'scale(1)' }, { transform: 'scale(1.06)' }, { transform: 'scale(1)' }],
            { duration: 360, easing: 'cubic-bezier(0.22,1,0.36,1)' }
          )
        }
      }
      requestAnimationFrame(frame)
    }
    if (counters.length) {
      if (!('IntersectionObserver' in window)) {
        counters.forEach(runCount)
      } else {
        const cntObs = new IntersectionObserver(
          (entries) => {
            entries.forEach((e) => {
              if (e.isIntersecting) {
                runCount(e.target as HTMLElement)
                cntObs.unobserve(e.target)
              }
            })
          },
          { threshold: 0.6 }
        )
        counters.forEach((c) => cntObs.observe(c))
        cleanups.push(() => cntObs.disconnect())
      }
    }

    // Star-burst on primary action
    if (!reduceMotion) {
      const onCelebrate = (ev: MouseEvent) => {
        const star = document.createElement('span')
        star.className = 'star-burst'
        star.setAttribute('aria-hidden', 'true')
        star.style.left = ev.clientX + 'px'
        star.style.top = ev.clientY + 'px'
        document.body.appendChild(star)
        star.addEventListener('animationend', () => star.remove())
      }
      const celebrators = Array.from(el.querySelectorAll<HTMLElement>('[data-celebrate]'))
      celebrators.forEach((c) => c.addEventListener('click', onCelebrate))
      cleanups.push(() =>
        celebrators.forEach((c) => c.removeEventListener('click', onCelebrate))
      )
    }

    return () => cleanups.forEach((fn) => fn())
  }, [])

  return (
    <div className="landing" ref={root}>
      {/* Nav */}
      <header className="nav" data-nav>
        <div className="nav__inner">
          <Link className="nav__brand" href="/">
            <span className="boot" aria-hidden="true"></span>SprachBoot
          </Link>
          <nav className="nav__center" aria-label="Primary">
            <a className="nav__link" href="#how">How it works</a>
            <a className="nav__link" href="#features">Features</a>
            <a className="nav__link" href="#plan">The plan</a>
          </nav>
          <div className="nav__right">
            <button className="nav__signin" type="button" onClick={enter}>Sign in</button>
            <button className="btn" type="button" onClick={enter} data-celebrate>Start practicing</button>
          </div>
        </div>
      </header>

      <main id="top">
        {/* Hero */}
        <section className="section hero" aria-labelledby="hero-h">
          <div className="hero__copy">
            <p className="hero__lead">Deutsch fürs echte Leben — Arzt, Uni, Büro</p>
            <h1 id="hero-h" className="reveal">Speak German <br />from day one.</h1>
            <p className="hero__sub reveal">
              SprachBoot is a conversation partner that talks back, catches your mistakes, and{' '}
              <em>remembers</em> them — so every session is a little easier than the last.
            </p>
            <div className="hero__actions reveal">
              <button className="btn btn--lg" type="button" onClick={enter} data-celebrate>Start practicing</button>
              <a className="link-cta" href="#how">See how it works <span className="btn__arrow" aria-hidden="true">↓</span></a>
            </div>
          </div>

          {/* live correction demo */}
          <div
            className="demo reveal"
            role="img"
            aria-label="Example: a learner says 'ich wandern gehe an der nähe', SprachBoot replies in German and corrects the word order to 'ich gehe wandern'."
          >
            <div className="demo__head">
              <span className="demo__title">Today · daily life</span>
              <span className="mono-label">A1 · VOICE</span>
            </div>
            <p className="bubble bubble--user" aria-hidden="true">ich wandern gehe an der nähe</p>
            <p className="bubble bubble--ai" aria-hidden="true">Oh schön! Wie lange gehst du normalerweise wandern?</p>
            <div className="correction" aria-hidden="true">
              <div className="correction__row">
                <s>ich wandern gehe</s>
                <span className="correction__arrow">→</span>
                <b>ich gehe wandern</b>
              </div>
              <p className="correction__note">The verb takes second place. (V2 word order)</p>
            </div>
            <span className="demo__boot" aria-hidden="true"></span>
          </div>
        </section>

        {/* Features */}
        <section className="section" id="features" aria-labelledby="feat-h">
          <div className="section__head reveal">
            <h2 id="feat-h">A whole tutor, in one conversation.</h2>
            <p>No lessons to schedule, no decks to grind. You talk; SprachBoot does the rest.</p>
          </div>

          <div className="bento">
            <article className="cell cell--feature tint-pear span-2x2 reveal">
              <span className="mono-label cell__tag">Voice &amp; chat</span>
              <h3>Talk, don’t study.</h3>
              <p>Hold the mic and just speak. Broken German is the whole point — SprachBoot replies in German at your level and keeps the conversation moving. Type instead if you’d rather. Either way, you’re practising the thing you actually need: talking.</p>
            </article>

            <article className="cell tint-cyan span-1x1 reveal">
              <span className="mono-label cell__tag">Corrections</span>
              <h3>Caught, not nagged.</h3>
              <p>Wrong case, wrong order, false friends — explained once, never red-penned to death.</p>
            </article>

            <article className="cell cell--radar tint-coral span-2x1 reveal">
              <span className="mono-label cell__tag">English-interference radar</span>
              <div className="fix-row"><s>ich habe ein auto</s> <span className="correction__arrow">→</span> <b>ich habe ein Auto</b></div>
              <div className="fix-row"><s>ich will become besser</s> <span className="correction__arrow">→</span> <b>ich will besser werden</b></div>
            </article>

            <article className="cell tint-lav span-1x2 reveal">
              <span className="mono-label cell__tag">Memory</span>
              <h3>Remembers what you forget.</h3>
              <p>Words you keep missing come back exactly when you’re about to lose them. Spaced repetition runs quietly underneath every chat — you never touch a flashcard.</p>
            </article>

            <article className="cell tint-mint span-1x1 reveal">
              <span className="mono-label cell__tag">Tests</span>
              <h3>Know your level.</h3>
              <p>Weekly check-ins use the same questions, so an A1 → A2 → B1 score actually means something.</p>
            </article>

            <article className="cell tint-pear span-1x1 reveal">
              <span className="mono-label cell__tag">B1 &amp; up</span>
              <h3>Talk shop in German.</h3>
              <p>Reach B1 and the engineering &amp; EV vocabulary for uni and the office turns up in conversation.</p>
            </article>
          </div>
        </section>

        {/* How it works */}
        <section className="section section--band band-cyan" id="how" aria-labelledby="how-h">
          <div className="section__inner">
            <div className="section__head reveal">
              <h2 id="how-h">One loop, getting smarter.</h2>
              <p>Every turn teaches SprachBoot something about how you speak. The next turn uses it.</p>
            </div>

            <div className="loop">
              <div className="loop__step reveal">
                <div className="loop__num">01</div>
                <div className="loop__body">
                  <h3>You speak.</h3>
                  <p>Voice or text, in whatever German you’ve got. Messy is fine.</p>
                </div>
              </div>
              <div className="loop__step reveal">
                <div className="loop__num">02</div>
                <div className="loop__body">
                  <h3>It replies in German.</h3>
                  <p>Short, natural, at your level — and switches to English for one quick note only when something really breaks.</p>
                </div>
              </div>
              <div className="loop__step reveal">
                <div className="loop__num">03</div>
                <div className="loop__body">
                  <h3>Your mistakes get analysed.</h3>
                  <p>Word order, gender, case, false friends — sorted by what trips you up most, quietly in the background.</p>
                </div>
              </div>
              <div className="loop__step reveal">
                <div className="loop__num">04</div>
                <div className="loop__body">
                  <h3>Your profile updates.</h3>
                  <p>Confident words, weak patterns, words due for review — all kept so the next conversation can lean on them.</p>
                </div>
              </div>
              <div className="loop__step reveal">
                <div className="loop__num">05</div>
                <div className="loop__body">
                  <h3>The next session is easier.</h3>
                  <p>It weaves in what you nearly forgot and gently presses on what you’re still getting wrong.</p>
                </div>
              </div>
            </div>
            <p className="loop__back reveal"><span aria-hidden="true">↻</span> and back to 01, every day</p>
          </div>
        </section>

        {/* The plan */}
        <section className="section section--band band-coral" id="plan" aria-labelledby="plan-h">
          <div className="section__inner plan">
            <div className="plan__counter reveal">
              <span className="plan__num"><span className="hl" data-count-to="6">0</span></span>
              <span className="mono-label plan__unit">months — the plan</span>
            </div>
            <div className="plan__copy reveal">
              <h2 id="plan-h">A1 to B1, about fifteen minutes a day.</h2>
              <p>
                That’s the target SprachBoot is built around: conversational B1 in roughly six
                months of daily practice. No grammar tables, no listening drills — just talking,
                a bit every day. Your real progress is whatever you put in.
              </p>
              <div className="plan__meta">
                <div><span>~15 min</span><span>a day, speaking</span></div>
                <div><span>A1 → B1</span><span>the path, step by step</span></div>
                <div><span>Daily</span><span>one short conversation</span></div>
              </div>
            </div>
          </div>
        </section>

        {/* Start strip */}
        <section className="section start" id="start" aria-labelledby="start-h">
          <h2 id="start-h" className="reveal">Genug geredet. Fang an.</h2>
          <p className="reveal">Enough about it — start talking. Your first conversation is one tap away.</p>
          <button className="btn btn--lg reveal" type="button" onClick={enter} data-celebrate>
            Start practicing <span className="btn__arrow" aria-hidden="true">→</span>
          </button>
        </section>
      </main>

      {/* Footer */}
      <footer className="foot" aria-label="Footer">
        <div className="foot-marquee">
          <div className="foot-marquee__track" aria-hidden="true">
            <span>SprachBoot <span className="dot">·</span> sprich mehr Deutsch <span className="dot">·</span> A1&nbsp;→&nbsp;B1 <span className="dot">·</span> jeden Tag <span className="dot">·</span>&nbsp;</span>
            <span>SprachBoot <span className="dot">·</span> sprich mehr Deutsch <span className="dot">·</span> A1&nbsp;→&nbsp;B1 <span className="dot">·</span> jeden Tag <span className="dot">·</span>&nbsp;</span>
          </div>
        </div>
        <div className="foot__meta">
          <span>Built for learners &amp; newcomers in Germany.</span>
          <span>SprachBoot · 2026</span>
        </div>
      </footer>
    </div>
  )
}
