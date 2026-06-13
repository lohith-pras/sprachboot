# SprachBoot — Frontend

Next.js 16 (App Router) + TypeScript + Tailwind frontend for **SprachBoot**, an AI-powered
German conversational fluency trainer. Speech-first: you talk (or type) broken German, the AI
converses back, errors are analyzed post-turn, and a **Growth Receipt** shows you what you can
now say that you couldn't before.

Pairs with the FastAPI backend in [`../backend`](../backend). The frontend is a thin client —
all conversation, error analysis, memory, scoring, and the receipt live in the backend.

## Prerequisites

- [Bun](https://bun.sh) ≥ 1.3 (package manager + runner — this project no longer uses npm)
- The backend running locally (see [`../backend/README.md`](../backend/README.md)), default
  `http://localhost:8000`

## Getting Started

```bash
bun install            # install deps (uses bun.lock)
bun run dev            # start the dev server on http://localhost:3000
```

Open [http://localhost:3000](http://localhost:3000).

### Scripts

```bash
bun run dev            # next dev (Turbopack, HMR)
bun run build          # production build
bun run start          # serve the production build
bun run lint           # eslint
bunx tsc --noEmit      # typecheck only
```

## Environment

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000   # backend base URL
```

`API_BASE` falls back to `http://localhost:8000` if unset (see [`lib/api.ts`](lib/api.ts)).

## Routes

| Route | Purpose |
|---|---|
| `/` | Landing |
| `/onboard` | First-run setup (name, API keys) |
| `/dashboard` | Home / overview |
| `/speak` | Main practice — voice + chat conversation, post-turn corrections, end-of-session **Growth Receipt** |
| `/test` | CEFR weekly/monthly tests |
| `/analytics` | Recharts dashboards (score trend, error breakdown, heatmap) |
| `/settings` | Models + API keys |
| `/review` | Spaced-repetition review |

## Structure

```
frontend/
├── app/                 # App Router pages (route = folder)
├── components/          # ChatBubble, ErrorOverlay, LevelBadge, ProgressRing, …
├── hooks/               # useSessionTimer, useVoiceRecorder, useErrorPoll
├── lib/                 # api.ts (backend client), types.ts
└── bun.lock             # bun lockfile (committed)
```

## Growth Receipt (`/speak`)

Ending a session calls `POST /session/end` then `GET /session/{id}/receipt`. The receipt screen
foregrounds your **corrected** German ("look what you said"), shows a **provisional** fluency
score, and a delta scoped to prior same-topic sessions (or a "baseline set" state on your first
couple of sessions). Types: [`lib/types.ts`](lib/types.ts) → `Receipt`.

## Notes

- **This is not the Next.js in your training data.** APIs/conventions may differ — read
  `node_modules/next/dist/docs/` before writing code (see [`AGENTS.md`](AGENTS.md)).
- Voice uses the browser `MediaRecorder` → backend Whisper transcription; TTS uses browser
  `speechSynthesis`. No audio is stored.
