export default function Footer() {
  return (
    <footer className="foot" aria-label="Footer">
      <div className="foot-marquee">
        <div className="foot-marquee__track" aria-hidden="true">
          <span>
            SprachBoot <span className="dot">·</span> sprich mehr Deutsch{' '}
            <span className="dot">·</span> A1&nbsp;→&nbsp;B1{' '}
            <span className="dot">·</span> jeden Tag <span className="dot">·</span>&nbsp;
          </span>
          <span>
            SprachBoot <span className="dot">·</span> sprich mehr Deutsch{' '}
            <span className="dot">·</span> A1&nbsp;→&nbsp;B1{' '}
            <span className="dot">·</span> jeden Tag <span className="dot">·</span>&nbsp;
          </span>
        </div>
      </div>
      <div className="foot__meta">
        <span>Built for learners &amp; newcomers in Germany.</span>
        <span>SprachBoot · 2026</span>
      </div>
    </footer>
  )
}
