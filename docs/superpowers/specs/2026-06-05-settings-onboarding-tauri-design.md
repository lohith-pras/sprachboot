# Spec A — Settings, Onboarding & Tauri Desktop Build

> **Branch:** `feat/app-dev`
> **Date:** 2026-06-05
> **Status:** Approved design, ready for implementation plan
> **Scope:** Group 1 of the SprachBoot development roadmap (features 1 + 2)

---

## 0. Goal

Turn SprachBoot into a distributable cross-platform desktop app (macOS + Windows)
with secure in-app API key management, user-selectable OpenRouter models, and a
first-run onboarding flow that asks for the user's name.

Two related but separable deliverables:

1. **Settings + Onboarding** — in-app management of API keys (OS keychain),
   model selection, and user name. Prerequisite for desktop packaging because a
   bundled app cannot rely on a hand-edited `.env` file.
2. **Tauri desktop build** — wrap the existing Next.js + FastAPI stack in a
   Tauri v2 shell, ship `.dmg` (macOS) and `.exe` (Windows) via GitHub Actions CI.

**Non-goals:** Linux build (future), auto-update (future), multi-user/multi-tenant
(this is a single-user local app).

---

## 1. Context

Current state (as of `feat/app-dev`):

- Monorepo: `frontend/` (Next.js 14 App Router) + `backend/` (FastAPI, Python 3.11, `uv`).
- `start.py` launches both servers and opens the browser at `localhost:3000`.
- Frontend `/app/api/*` routes are **thin proxies** to FastAPI (recently refactored
  into `frontend/lib/backend-proxy.ts` with `proxyGet`/`proxyPost`/`proxyFormData`).
- `openrouter_client.py` is the shared OpenRouter HTTP wrapper; models are
  hardcoded (`LLAMA_MODEL`, `DEEPSEEK_MODEL`).
- API keys read from environment via `os.getenv` / `python-dotenv`.
- Dashboard greeting hardcodes `"Lo"` in `frontend/app/page.tsx`.

---

## 2. Database

Add a single-row `user_preferences` table to the existing SQLAlchemy models
(`backend/models/db.py`). API keys are **never** stored here — only in the OS keychain.

```sql
CREATE TABLE user_preferences (
    id                  INTEGER PRIMARY KEY DEFAULT 1,
    user_name           TEXT    NOT NULL DEFAULT 'User',
    conv_model          TEXT    DEFAULT 'meta-llama/llama-3.3-70b-instruct',
    analysis_model      TEXT    DEFAULT 'deepseek/deepseek-v4-flash',
    onboarding_complete BOOLEAN DEFAULT FALSE
);
```

- Enforced single row (id always 1). A helper `get_or_create_preferences(db)`
  returns the row, creating defaults on first access.
- SQLAlchemy model `UserPreferences` added alongside existing models.

---

## 3. Backend — `backend/routers/settings.py`

New router, registered in `main.py`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/settings/preferences` | GET | Returns `user_name`, `conv_model`, `analysis_model`, `onboarding_complete` |
| `/settings/preferences` | PUT | Updates any subset of the above |
| `/settings/apikey` | POST | `{service, key}` → `keyring.set_password("SprachBoot", service, key)` |
| `/settings/apikey/status` | GET | `{openrouter: bool, openai: bool, deepl: bool}` — presence only, never returns the key |
| `/settings/apikey/test` | POST | `{service}` → lightweight ping to validate the stored key, returns `{ok: bool}` |
| `/settings/models` | GET | Calls OpenRouter `/api/v1/models`, filters to chat-capable models, caches 1 hr in memory |

### Keyring integration

- Add `keyring` to backend dependencies (`pyproject.toml`).
- Service name constant: `KEYRING_SERVICE = "SprachBoot"`.
- Key names: `"openrouter"`, `"openai"`, `"deepl"`.

### `openrouter_client.py` changes

- Resolve the API key at call time:
  `keyring.get_password(KEYRING_SERVICE, "openrouter")`, falling back to
  `os.getenv("OPENROUTER_API_KEY")` for dev.
- Resolve model IDs from `user_preferences` (conv vs analysis) instead of module
  constants. Callers (`conversation.py`, `error_analysis.py`) pass the resolved
  model ID, or the client reads preferences. Keep `LLAMA_MODEL` / `DEEPSEEK_MODEL`
  as fallback defaults.

---

## 4. Frontend — Onboarding wizard (`/onboard`)

Shown only when `onboarding_complete = false`. The root layout checks preferences
on load and redirects to `/onboard` when onboarding is incomplete.

- **Step 1 — Name:** "What should I call you?" text input → sets `user_name`.
- **Step 2 — API keys:** masked inputs for OpenRouter (required), OpenAI (required
  for Whisper/embeddings), DeepL (optional). Each has a "Test connection" button
  hitting `/settings/apikey/test`.
- **Step 3 — Models:** searchable dropdown from `GET /settings/models`. Pre-selected
  to Llama 3.3 70B (conversation) + DeepSeek Flash (analysis). Defaults acceptable.

On completion: `PUT /settings/preferences {onboarding_complete: true}` → redirect to `/`.

---

## 5. Frontend — Settings page (`/settings`)

Non-wizard layout, two panels:

- **Account:** name field + save.
- **AI Configuration:** API key fields (each shows ✓/✗ from `/settings/apikey/status`),
  conversation + analysis model dropdowns. DeepL key field included (optional).

Dashboard `page.tsx`: replace hardcoded `"Lo"` with `user_name` fetched from
`GET /settings/preferences`.

---

## 6. Tauri desktop build

### 6a. Frontend prerequisite changes

- **Delete `/app/api/` directory** — the entire proxy layer (including the
  recently-added `backend-proxy.ts` usage) becomes redundant.
- Point all frontend fetches directly at FastAPI via `NEXT_PUBLIC_API_URL`
  (already in `.env.local`, defaults `http://localhost:8000`). Find-and-replace
  across hooks (`useErrorPoll`, `useVoiceRecorder`) and pages (`speak`, `page.tsx`,
  `test`, `analytics`, `review`).
- Add CORS middleware to FastAPI allowing `tauri://localhost` and
  `http://localhost:3000` origins.

### 6b. Static frontend served by FastAPI

- `next build` configured for static export (`output: 'export'` → `out/`).
- FastAPI mounts the exported frontend via `StaticFiles` so a single process
  serves both UI and API in the packaged app.

### 6c. Tauri scaffold (`src-tauri/` at repo root)

- `tauri.conf.json`: window title "SprachBoot", 1200×800 default,
  macOS bundle id `com.sprachboot.app`.
- `main.rs`: on startup spawn the Python sidecar, open the window; on window
  close, kill the sidecar. (~50 lines of Rust, declarative config otherwise.)

### 6d. Python sidecar

- Bundle FastAPI (+ all deps incl. faster-whisper) as a single binary via
  **PyInstaller**: output `sprachboot-server`.
- Registered as a Tauri sidecar (`externalBin`).
- **Risk note:** faster-whisper model weights and ChromaDB native deps must be
  bundled or downloaded on first run. PyInstaller spec must account for these;
  validate sidecar size and cold-start during implementation.

### 6e. CI — `.github/workflows/release.yml`

- Trigger: push to `feat/app-dev` or tag `v*`.
- Matrix: `[macos-latest, windows-latest]`.
- macOS job → `.dmg`. Windows job → `.exe` (NSIS installer).
- Each runner: build Next.js static, run PyInstaller for the sidecar, run
  `tauri build`, upload installer to GitHub release artifacts.

---

## 7. Build order

1. `user_preferences` table + `settings.py` router + keyring wiring.
2. `openrouter_client.py` reads key from keyring + model from preferences.
3. `/onboard` wizard + root-layout redirect gate.
4. `/settings` page + dashboard name swap.
5. Frontend: delete `/app/api/`, repoint fetches, add CORS.
6. Static export + FastAPI `StaticFiles` mount.
7. PyInstaller sidecar spec.
8. Tauri scaffold + sidecar wiring + local `.dmg`/`.exe` build.
9. GitHub Actions CI matrix.

---

## 8. Open risks

- **PyInstaller + faster-whisper + ChromaDB** bundling is the highest-risk item.
  Validate early (step 7) before investing in Tauri config.
- **macOS code signing / notarization** for `.dmg` distribution outside the App
  Store — deferred; unsigned builds run with a Gatekeeper warning for now.
- **Static export vs dynamic routes** — confirm no remaining Next.js feature
  depends on a Node runtime after the proxy routes are deleted.
