# SprachBoot — Clean Webapp Design

> Date: 2026-06-05
> Status: Approved, in implementation

## Scope

Local-only webapp for personal testing (owner + one friend, ~1–2 months).
OpenRouter for conversation + error analysis. Whisper STT and embeddings
already run locally. No hosting, no OpenAI, no desktop packaging.

## Context (current state)

- `frontend/` — Next.js 16 App Router, `output: 'export'`.
- `backend/` — FastAPI + SQLite + ChromaDB, also bundled as a PyInstaller
  sidecar binary.
- `src-tauri/` (root) — Tauri 2 desktop wrapper, spawns the Python sidecar,
  builds dmg + nsis. Source of macOS Gatekeeper pain (ad-hoc signing).
- `website/` — standalone static marketing landing (index.html + css + js).
- `start.py` — dev launcher (boots backend + frontend, opens browser).

Key finding: **OpenAI is already unused.** STT = local `faster-whisper`,
embeddings = ChromaDB built-in local model, translation = DeepL. The OpenAI key
is only collected in onboarding and pinged by a settings "test" endpoint — no
feature consumes it.

## 1. De-Tauri

Delete from working tree (recoverable from git history):

- `src-tauri/` (root)
- `backend/src-tauri/`
- `backend/sprachboot-server.spec`
- `backend/build/`, `backend/dist/` (PyInstaller output)
- `.github/workflows/release.yml`

Published `v0.1.2` / `main` release installers stay on GitHub; installed copies
keep working. App becomes a pure local webapp via `start.py`. Kills Gatekeeper.

## 2. Landing page (port + namespace)

- Port `website/index.html` → `app/page.tsx` (new `/`).
- Scope landing CSS under a `.landing` wrapper (merge `tokens.css`) so it cannot
  collide with the app's `.nav` / `.btn` / `.hero` rules.
- Reveal/celebrate JS → a small client-side effect.
- CTAs ("Start practicing" / "Sign in") → `/dashboard`.
- Delete `website/` after porting.

## 3. Routing

- Dashboard: `app/page.tsx` → `app/dashboard/page.tsx`.
- App `Nav` / `Footer` render only on app routes; `/` and `/onboard` get no app
  chrome (landing brings its own nav).
- Fix `/`-pointing links (nav brand, post-onboarding redirect) → `/dashboard`.

## 4. Onboarding fixes

- **Flash → redirect:** `OnboardingGate` guards render until the preferences
  check resolves (no dashboard flash). Runs once at root, not refetched per
  navigation. App routes redirect incomplete users to `/onboard`.
- **Saved feedback:** key save/test shows a clear persisted state
  (✓ Saved / ✓ Connected / ✗ error) in onboarding and settings.
- **OpenRouter-only:** onboarding requires only OpenRouter. OpenAI removed from
  the onboarding flow; DeepL optional. Optionally strip OpenAI from
  `keychain.KNOWN_KEYS` / schemas / settings router as well.

## 5. Friend-ready local run

- README: clone → install Node + uv → `python start.py`. Note first-run Whisper
  model download (~460MB) and that API keys are entered in-app via onboarding.
- Verify `start.py` still works after de-Tauri.

## 6. Future: Deployment (documented only, not built)

Hosted path for later phone / Android-PWA access:

- Frontend → Vercel (static export).
- Backend → Fly.io / Render (FastAPI in Docker).
- Relational DB → Neon Postgres (replaces SQLite).
- Vector memory → Qdrant Cloud (replaces local ChromaDB).
- Secrets → server env vars (replaces OS keychain).
- Auth → single shared password / token (public URL needs a lock).
- HTTPS required for mic (`getUserMedia`) + PWA.
- Cost ~$0–7/mo. Android = PWA (install-to-home-screen), same repo, no rewrite.

Make config env-driven now (`NEXT_PUBLIC_API_URL` already is) so this later step
stays small.

## Non-goals

Hosting, auth, OpenAI, desktop packaging, DB migration, Android build — all
deferred to the documented future path.
