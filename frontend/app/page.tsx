import Link from 'next/link'
import LevelBadge from '@/components/LevelBadge'

export const metadata = {
  title: 'SprachBoot — Dashboard',
}

export default async function Home() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  let profile = { current_level: 'A1', words_confident: 0, words_learning: 0, total_sessions: 0, sessions_this_week: 0, v2_accuracy: 0.0, latest_test_score: 0.0 };
  try {
    const res = await fetch(`${API_URL}/profile/summary`, { cache: 'no-store' });
    if (res.ok) profile = await res.json();
  } catch (e) {
    console.error('Failed to fetch profile', e);
  }

  return (
    <main>
      <div className="dashboard">
        <div className="dashboard__welcome">
          <h1>Guten Tag, Lo. 👋</h1>
          <p>Ready for today&apos;s conversation?</p>
        </div>

        <div className="bento">
          {/* Quick start — 2×1 */}
          <article className="cell tint-pear span-2x1">
            <span className="mono-label cell__tag">Today&apos;s session</span>
            <h3>Start a conversation</h3>
            <p>
              Pick a topic and start talking in German. Messy is fine — that&apos;s the point.
              SprachBoot replies at your level and keeps it moving.
            </p>
            <div style={{ marginTop: 'var(--space-xl)' }}>
              <Link className="btn" href="/speak">
                Talk to AI
              </Link>
            </div>
          </article>

          {/* Quick Stats */}
          <article className="cell tint-paper">
            <span className="mono-label cell__tag">Your Profile</span>
            <h3>
              <LevelBadge level={profile.current_level as any} />
            </h3>
            <ul style={{ marginTop: 'var(--space-md)', listStyle: 'none', color: 'var(--color-ink-2)' }}>
              <li><strong>{profile.words_confident}</strong> confident words</li>
              <li><strong>{profile.words_learning}</strong> learning words</li>
              <li><strong>{profile.total_sessions}</strong> total sessions</li>
            </ul>
          </article>

          {/* Review Mode */}
          <article className="cell tint-mint">
            <span className="mono-label cell__tag">Daily Review</span>
            <h3>Spaced Repetition</h3>
            <p>
              Practice your weak patterns and low confidence words with rapid-fire roleplay.
            </p>
            <Link
              className="btn btn--outline"
              href="/review"
              style={{ marginTop: 'var(--space-md)', display: 'inline-flex' }}
            >
              Start Review
            </Link>
          </article>

          {/* Level Progress */}
          <article className="cell tint-paper">
            <span className="mono-label cell__tag">Next Level: A2</span>
            
            <div style={{ marginTop: 'var(--space-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>
                <span>Grammar (V2)</span>
                <span>{Math.round(profile.v2_accuracy * 100)}% / 65%</span>
              </div>
              <div style={{ height: '8px', background: 'var(--color-rule)', borderRadius: '4px', marginTop: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min((profile.v2_accuracy / 0.65) * 100, 100)}%`, height: '100%', background: 'var(--color-accent)' }}></div>
              </div>
            </div>

            <div style={{ marginTop: 'var(--space-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>
                <span>Vocabulary</span>
                <span>{profile.words_confident} / 200</span>
              </div>
              <div style={{ height: '8px', background: 'var(--color-rule)', borderRadius: '4px', marginTop: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min((profile.words_confident / 200) * 100, 100)}%`, height: '100%', background: 'var(--color-accent-2)' }}></div>
              </div>
            </div>

            <div style={{ marginTop: 'var(--space-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>
                <span>Recent Test</span>
                <span>{Math.round(profile.latest_test_score * 100)}%</span>
              </div>
              <div style={{ height: '8px', background: 'var(--color-rule)', borderRadius: '4px', marginTop: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${profile.latest_test_score * 100}%`, height: '100%', background: 'var(--color-accent-3)' }}></div>
              </div>
            </div>
          </article>

          {/* Weekly test */}
          <article className="cell tint-lav">
            <span className="mono-label cell__tag">Weekly test</span>
            <h3>Know your level.</h3>
            <p>
              Take the same 10-question check-in every week to track real,
              comparable progress.
            </p>
            <Link
              className="btn btn--soft"
              href="/test"
              style={{ marginTop: 'var(--space-md)', display: 'inline-flex' }}
            >
              Take test
            </Link>
          </article>

        </div>
      </div>
    </main>
  )
}
