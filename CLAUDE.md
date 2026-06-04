# SprachBoot — CLAUDE.md Build Specification
> AI-powered German conversational fluency trainer
> Target: A1 → B1 in 6 months, daily practice, speech-first, no traditional study

---

## 0. Project Identity

**App name:** SprachBoot  
**Goal:** Help an A1-level Elektromobilität M.Sc. student reach B1 conversational German  
**Primary user:** Lo — Kannada/English speaker, lives in Nürnberg, needs German for doctor, uni, office  
**Target B2+ layer:** Engineering/EV vocabulary injected at B1 milestone  
**Non-goals:** Reading practice, listening drills, grammar tables, flashcard decks  
**Core loop:** Speak (or type) broken German → AI converses back → errors analyzed post-turn → memory updated → next session is smarter  

---

## 1. Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript | |
| Styling | Tailwind CSS | dark theme, minimal |
| Speech → Text | OpenAI Whisper API (`whisper-1`) | fallback: browser Web Speech API |
| Conversation model | Llama 3.3 70B Instruct via OpenRouter | `meta-llama/llama-3.3-70b-instruct` |
| Error analysis model | DeepSeek V4 Flash via OpenRouter | `deepseek/deepseek-v4-flash` — structured JSON output |
| Backend | FastAPI (Python 3.11+) | |
| Structured memory DB | SQLite (dev) → Postgres (prod) | per-word and per-pattern stats |
| Semantic memory | ChromaDB (local) | embedded sentences for RAG context injection |
| Embeddings | `text-embedding-3-small` via OpenAI API | cheap, fast |
| Analytics charts | Recharts (React) | |
| Spaced repetition | Custom logic (no external lib) | based on SM-2 algorithm |

---

## 2. File Structure

```
sprachboot/
├── CLAUDE.md                    ← this file
├── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             ← dashboard / home
│   │   ├── speak/
│   │   │   └── page.tsx         ← main conversation mode (voice + chat)
│   │   ├── test/
│   │   │   └── page.tsx         ← weekly/monthly CEFR test
│   │   └── analytics/
│   │       └── page.tsx         ← dashboard with charts
│   ├── components/
│   │   ├── VoiceRecorder.tsx    ← Whisper mic component
│   │   ├── ChatBubble.tsx       ← message display
│   │   ├── ErrorOverlay.tsx     ← post-turn correction display
│   │   ├── ProgressRing.tsx     ← word confidence ring
│   │   ├── WeeklyReport.tsx     ← analytics summary card
│   │   └── LevelBadge.tsx       ← A1/A2/B1 etc badge
│   └── lib/
│       ├── openrouter.ts        ← OpenRouter API client (Gemma + DeepSeek)
│       └── whisper.ts           ← Whisper STT client
├── backend/
│   ├── main.py                  ← FastAPI app entry
│   ├── routers/
│   │   ├── session.py           ← POST /session/turn, POST /session/end
│   │   ├── test.py              ← GET/POST /test/weekly, /test/monthly
│   │   ├── profile.py           ← GET /profile/summary, /profile/weaknesses
│   │   └── analytics.py        ← GET /analytics/weekly, /analytics/heatmap
│   ├── services/
│   │   ├── conversation.py      ← builds Gemma prompt with RAG context
│   │   ├── error_analysis.py    ← calls DeepSeek, parses error JSON
│   │   ├── memory.py            ← reads/writes SQLite + ChromaDB
│   │   ├── profile_engine.py    ← computes word confidence, pattern scores
│   │   ├── spaced_repetition.py ← SM-2 interval calculation
│   │   └── test_engine.py       ← CEFR test generation + scoring
│   ├── models/
│   │   ├── db.py                ← SQLAlchemy models
│   │   └── schemas.py           ← Pydantic request/response schemas
│   └── data/
│       ├── cefr_a1_wordlist.json
│       ├── cefr_a2_wordlist.json
│       ├── b1_engineering_vocab.json    ← EV/Automotive domain words
│       └── test_prompts/
│           ├── weekly_a1.json
│           ├── weekly_a2.json
│           └── monthly_b1.json
└── chroma_db/                   ← ChromaDB persistence directory
```

---

## 3. Database Schema (SQLite → Postgres)

### Table: `sessions`
```sql
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_s  INTEGER,
    mode        TEXT,           -- 'voice' | 'chat'
    topic       TEXT,           -- 'daily_life' | 'uni' | 'engineering' | 'test'
    turn_count  INTEGER,
    overall_score REAL          -- 0.0–1.0 composite fluency score
);
```

### Table: `turns`
```sql
CREATE TABLE turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(id),
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_raw        TEXT,       -- what user said/typed (raw)
    user_corrected  TEXT,       -- corrected version from error analysis
    ai_response     TEXT,
    error_count     INTEGER,
    had_english_switch BOOLEAN  -- did AI switch to English this turn?
);
```

### Table: `errors`
```sql
CREATE TABLE errors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id         INTEGER REFERENCES turns(id),
    error_type      TEXT,       -- 'word_order' | 'gender' | 'case' | 'verb_form' | 'vocab' | 'false_friend'
    pattern_key     TEXT,       -- 'V2_violation' | 'dativ_after_mit' | 'noun_capitalisation' etc.
    severity        TEXT,       -- 'high' | 'medium' | 'low'
    user_fragment   TEXT,       -- what user said
    correct_form    TEXT,       -- what it should be
    rule_shown      BOOLEAN     -- was grammar rule displayed?
);
```

### Table: `word_stats`
```sql
CREATE TABLE word_stats (
    word            TEXT PRIMARY KEY,
    total_uses      INTEGER DEFAULT 0,
    correct_uses    INTEGER DEFAULT 0,
    confidence      REAL DEFAULT 0.0,   -- correct_uses / total_uses, weighted by recency
    last_seen       TIMESTAMP,
    cefr_level      TEXT,               -- 'A1' | 'A2' | 'B1' | 'B2'
    next_review     TIMESTAMP,          -- spaced repetition next due date
    interval_days   INTEGER DEFAULT 1   -- SM-2 interval
);
```

### Table: `pattern_stats`
```sql
CREATE TABLE pattern_stats (
    pattern_key     TEXT PRIMARY KEY,   -- e.g. 'V2_violation'
    error_type      TEXT,
    total_seen      INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    accuracy        REAL DEFAULT 0.0,
    last_error      TIMESTAMP,
    is_weak         BOOLEAN DEFAULT FALSE  -- flagged if accuracy < 0.6
);
```

### Table: `test_results`
```sql
CREATE TABLE test_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    test_type       TEXT,       -- 'weekly' | 'monthly'
    cefr_level      TEXT,       -- level being tested
    score           REAL,       -- 0.0–1.0
    sections        TEXT        -- JSON blob: {word_order, vocabulary, fluency}
);
```

---

## 4. API Contracts

### POST `/session/turn`
**Request:**
```json
{
  "session_id": 42,
  "user_input": "ich wandern gehe an der nähe",
  "mode": "voice",
  "topic": "daily_life"
}
```
**Response:**
```json
{
  "turn_id": 101,
  "ai_response": "Oh schön! Wie lange gehst du normalerweise wandern?",
  "english_switch": false,
  "errors": [
    {
      "error_type": "word_order",
      "pattern_key": "V2_violation",
      "severity": "high",
      "user_fragment": "ich wandern gehe",
      "correct_form": "ich gehe wandern",
      "rule_shown": false
    }
  ],
  "corrected_input": "Ich gehe in der Nähe wandern."
}
```

### GET `/profile/weaknesses`
**Response:**
```json
{
  "top_weak_patterns": [
    {"pattern_key": "V2_violation", "accuracy": 0.31, "error_count": 14},
    {"pattern_key": "dativ_after_mit", "accuracy": 0.43, "error_count": 7}
  ],
  "low_confidence_words": ["bekommen", "obwohl", "trotzdem"],
  "current_level_estimate": "A1+",
  "days_to_next_level": 42
}
```

### GET `/analytics/weekly`
**Response:**
```json
{
  "week": "2025-W23",
  "sessions": 6,
  "total_minutes": 187,
  "turns_total": 214,
  "error_rate_trend": [0.71, 0.68, 0.65, 0.61, 0.59, 0.58],
  "best_day": "Wednesday",
  "pattern_improvements": ["noun_capitalisation"],
  "pattern_regressions": [],
  "words_added_to_confident": 12
}
```

### POST `/test/weekly`
**Request:** `{ "level": "A1" }`  
**Response:** CEFR test JSON (see Section 7)

---

## 5. Core Services

### 5a. `conversation.py` — Gemma Prompt Builder

This service builds the system prompt for Llama. It:
1. Calls `memory.py` to retrieve top 5 weak patterns and 10 low-confidence words
2. Calls ChromaDB to retrieve the 5 most similar past utterances (for context)
3. Injects this as RAG context into the system prompt
4. Switches to English explanation if `english_switch_trigger` fires (see logic below)

**System prompt template:**
```
You are a friendly German conversation partner helping a learner reach B1 conversational fluency.
The learner is an Indian student in Nürnberg, studying Elektromobilität at FAU.

LEARNER PROFILE (from memory):
- Current level: {current_level}
- Recurring weak patterns: {weak_patterns}
- Low-confidence words to weave in naturally: {low_conf_words}

CONVERSATION RULES:
1. Always respond in German at {current_level} difficulty
2. Keep responses SHORT — 1–2 sentences max. You are a conversation partner, not a teacher.
3. If the learner makes a SEVERE error (V2 violation, wrong gender + case together), 
   briefly switch to English to explain ONE thing, then immediately return to German.
   Format: "[EN: Quick explanation] Auf Deutsch: [your response]"
4. Do NOT correct every small mistake — only high-severity or recurring patterns
5. Topics should feel natural: daily life, uni, city, food, work
6. From B1 onward, weave in engineering/EV topics when natural
7. Never lecture. Never give grammar tables. You are having a conversation.

PAST CONTEXT (last similar sessions):
{chroma_context}
```

**English switch trigger:** Fire if:
- `error_type == "word_order"` AND `severity == "high"` AND `pattern_stats[pattern_key].error_count > 3`
- OR learner types `"?"` or `"what?"` or `"ich verstehe nicht"`

### 5b. `error_analysis.py` — DeepSeek JSON Extractor

Runs *after* conversation turn, non-blocking (background task in FastAPI).

**DeepSeek prompt:**
```
You are a German language error analyzer. The learner said:
"{user_raw}"

The correct version is approximately:
"{hint_from_model}"

Analyze the learner's sentence and return ONLY valid JSON in this exact schema:
{
  "corrected": "string — the corrected German sentence",
  "errors": [
    {
      "error_type": "word_order|gender|case|verb_form|vocab|capitalisation|false_friend",
      "pattern_key": "short_snake_case_key",
      "severity": "high|medium|low",
      "user_fragment": "what the user said",
      "correct_form": "what it should be",
      "rule": "one-sentence grammar rule — only for high severity"
    }
  ]
}

RULES:
- Return ONLY JSON. No preamble, no markdown backticks.
- If no errors, return {"corrected": "{user_raw}", "errors": []}
- Severity guide: high = breaks comprehension or sounds very wrong, 
  medium = grammatically incorrect but understandable, low = style/preference
- pattern_key examples: V2_violation, verb_final_subordinate, 
  accusative_after_durch, noun_not_capitalised, false_friend_gift, 
  gender_article_wrong, dativ_after_mit
```

### 5c. `memory.py` — Unified Memory Service

Two stores:

**SQLite writes (every turn):**
- Upsert `word_stats` for every word in corrected sentence
- Insert all errors into `errors` table
- Update `pattern_stats` accuracy rolling average

**ChromaDB writes (every turn):**
- Embed the corrected sentence
- Store with metadata: `{session_id, timestamp, patterns_present, level}`
- Collection: `"user_utterances"`

**ChromaDB reads (before each turn):**
- Query with current user input embedding
- Return top 5 similar past utterances as context string

### 5d. `profile_engine.py` — Confidence & Level Estimator

**Word confidence formula:**
```python
# Recency-weighted confidence
def compute_confidence(correct_uses, total_uses, days_since_last_seen):
    base = correct_uses / max(total_uses, 1)
    recency_decay = 0.95 ** days_since_last_seen  # decay if not seen recently
    return round(base * recency_decay, 3)
```

**Level estimator:**
```python
def estimate_level(pattern_stats, word_stats, test_results):
    # A1: V2 accuracy < 50%, vocabulary < 200 confident words
    # A2: V2 accuracy > 65%, case accuracy > 50%, 200–600 confident words
    # B1: V2 accuracy > 80%, subordinate clause accuracy > 60%, 600+ confident words
    # Also factor in last test_result score
```

**Weak pattern flag:**
A pattern is `is_weak = True` if:
- `error_count >= 3` AND `accuracy < 0.60`

---

## 6. Frontend Pages

### `/speak` — Main Practice Page

**Layout:**
- Top bar: current level badge, session timer, topic selector
- Main area: chat bubble thread (user + AI alternating)
- Bottom: mic button (hold to speak) + text input toggle
- Right panel (collapsible): "Last correction" — shows corrected sentence with diffs highlighted
- After each AI turn: subtle error indicator (red dot count, not intrusive)
- Click red dot → opens ErrorOverlay with full breakdown

**Voice flow:**
1. User holds mic → Web Audio API records
2. On release → POST audio to `/session/turn` (multipart)
3. Backend: Whisper transcribes → Llama generates response → DeepSeek analyzes (background)
4. Frontend: shows AI text response immediately, plays TTS (optional — use browser speechSynthesis)
5. Error overlay updates ~1s later when DeepSeek analysis completes

**Chat mode toggle:**
Same page, mic replaced with text input. Everything else identical. No separate route.

### `/test` — CEFR Test Page

**Weekly test:**
- 10 questions, same format every week (allows score comparison)
- 3 sections: word order (4 questions), vocabulary (3 questions), conversation response (3 questions)
- Score stored, shown as trend chart

**Monthly test:**
- 20 questions, harder than weekly
- Additional section: extended conversation (AI rates 3-turn exchange)
- Triggers level recalibration

### `/analytics` — Dashboard Page

**Charts (Recharts):**
1. Score trend line (weekly test scores over time)
2. Error type breakdown (stacked bar: word_order / gender / case / vocab per week)
3. Session heatmap (calendar view — green = practiced, dark = missed)
4. Vocabulary growth curve (confident words over time)
5. Pattern accuracy table (sortable — worst first)

**Weekly report card** (auto-generated Monday morning):
- 3 highlights: what improved, what's still weak, one focus for this week
- Generated by calling DeepSeek with the weekly stats summary

---

## 7. CEFR Test Design

### A1 Weekly Test (10 questions, same format every week)

**Section 1 — Word Order (4 questions)**
Each question: shown a jumbled German sentence, must type it correctly.
Example: `"gehe / Heute / ich / Supermarkt / zum"` → `"Heute gehe ich zum Supermarkt."`
Scoring: exact match OR semantic equivalence check via DeepSeek

**Section 2 — Vocabulary (3 questions)**
Fill in the blank with correct word from 4 options.
Example: `"Ich ___ Hunger."` → Options: habe / bin / gehe / mache
Questions randomized from `cefr_a1_wordlist.json`

**Section 3 — Short Response (3 questions)**
AI asks a simple question, user responds in 1–2 sentences (voice or text).
Response scored on: word order accuracy, vocabulary appropriateness, comprehensibility.
Scored by DeepSeek on 0–10 scale per response.

**A1 Baseline test (Day 1 only):**
Same format, 20 questions, 2x each section. Establishes starting score. Stores in `test_results` as `test_type = "baseline"`.

### A2 Monthly Test (20 questions)
Same structure, harder vocabulary, subordinate clause word order, case prepositions.

---

## 8. English Interference Module

Activated automatically from Day 1. The error analysis model is primed to flag these English→German interference patterns specifically:

| Pattern Key | Description | Example |
|---|---|---|
| `V2_violation` | Verb not in second position | "Ich wandern gehe" |
| `verb_final_missing` | Verb not at end in subordinate clause | "...weil ich gehe nach Hause" |
| `false_friend_gift` | Using false cognate | "Das ist ein Gift" (meaning present) |
| `false_friend_bekommen` | Using false cognate | "Ich will become besser" |
| `noun_not_capitalised` | German nouns must be capitalized | "ich habe ein auto" |
| `gender_article_wrong` | Wrong der/die/das | "der Arbeit" instead of "die Arbeit" |
| `dativ_after_mit` | Wrong case after "mit" | "mit mein Freund" |
| `accusative_after_durch` | Wrong case after "durch" | "durch der Stadt" |

These patterns get extra weight in the RAG context injection — always surfaced to Llama if recently triggered.

---

## 9. Engineering/EV Vocabulary Layer (B1+ unlock)

**Trigger:** `current_level_estimate >= "B1"` in `profile_engine.py`

**File:** `backend/data/b1_engineering_vocab.json`

```json
{
  "general_engineering": [
    {"de": "die Anforderung", "en": "requirement", "example": "Die Anforderungen des Systems sind klar."},
    {"de": "der Regelkreis", "en": "control loop", "example": "Der Regelkreis regelt die Temperatur."},
    {"de": "die Schnittstelle", "en": "interface", "example": "Die Schnittstelle zwischen den Modulen."},
    {"de": "auslegen", "en": "to design/dimension", "example": "Wir müssen das System neu auslegen."}
  ],
  "ev_automotive": [
    {"de": "das Bordnetz", "en": "vehicle electrical system", "example": "Das Bordnetz versorgt alle Verbraucher."},
    {"de": "die Reichweite", "en": "range", "example": "Die Reichweite des Fahrzeugs beträgt 400 km."},
    {"de": "der Ladezustand", "en": "state of charge (SoC)", "example": "Der Ladezustand des Akkus ist 80%."},
    {"de": "V2X-Kommunikation", "en": "vehicle-to-everything communication", "example": "V2X-Kommunikation verbessert die Verkehrssicherheit."}
  ],
  "office_professional": [
    {"de": "die Rückfrage", "en": "follow-up question", "example": "Ich habe noch eine Rückfrage."},
    {"de": "könnten Sie das bitte erklären?", "en": "could you explain that please?", "example": null},
    {"de": "ich verstehe das nicht ganz", "en": "I don't quite understand that", "example": null}
  ]
}
```

When B1 is reached, conversation topics in Llama prompt expand to include:
- `"Erkläre mir dein Forschungsprojekt"`
- `"Was ist ein Problem bei Elektroautos?"`
- `"Wie war dein Meeting heute?"`

---

## 10. Spaced Repetition (SM-2 implementation)

**File:** `backend/services/spaced_repetition.py`

```python
def update_interval(word: str, was_correct: bool, current_interval: int, db) -> int:
    """
    Simplified SM-2:
    - Correct: interval *= 2 (up to max 30 days)
    - Incorrect: reset interval to 1 day
    - next_review = today + new_interval
    """
    if was_correct:
        new_interval = min(current_interval * 2, 30)
    else:
        new_interval = 1
    
    next_review = datetime.now() + timedelta(days=new_interval)
    db.update_word_stats(word, interval_days=new_interval, next_review=next_review)
    return new_interval
```

Words are "due for review" when `next_review <= now`. The conversation engine prioritizes weaving due words into topics naturally — passed to Llama as `low_conf_words`.

---

## 11. Learning Pattern Detection (Month 2+)

**File:** `backend/services/profile_engine.py` → `detect_patterns()`

After 30+ sessions, compute:
```python
{
  "best_day_of_week": "Wednesday",   # highest avg score
  "best_time_of_day": "evening",     # 18:00–21:00
  "avg_retention_per_session_min": 0.8,  # score gain per minute practiced
  "plateau_detected": False,         # True if no score gain in 14 days
  "streak_current": 12,
  "streak_longest": 12
}
```

If `plateau_detected == True`:
- Inject a harder topic into next session
- Surface a specific grammar module (e.g., Konjunktiv II) as focus

---

## 12. OpenRouter API Integration

**File:** `frontend/lib/openrouter.ts`

```typescript
const OPENROUTER_BASE = "https://openrouter.ai/api/v1";
const LLAMA_MODEL = "meta-llama/llama-3.3-70b-instruct";
const DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash";

export async function callLlama(messages: Message[]): Promise<string> {
  const res = await fetch(`${OPENROUTER_BASE}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.OPENROUTER_API_KEY}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://sprachboot.vercel.app",
    },
    body: JSON.stringify({
      model: LLAMA_MODEL,
      messages,
      max_tokens: 200,  // Keep responses short
      temperature: 0.7,
    }),
  });
  const data = await res.json();
  return data.choices[0].message.content;
}

export async function callDeepSeekAnalysis(prompt: string): Promise<ErrorAnalysis> {
  const res = await fetch(`${OPENROUTER_BASE}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.OPENROUTER_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: DEEPSEEK_MODEL,
      messages: [{ role: "user", content: prompt }],
      max_tokens: 500,
      temperature: 0.1,  // Low temp for structured JSON
      response_format: { type: "json_object" },
    }),
  });
  const data = await res.json();
  return JSON.parse(data.choices[0].message.content) as ErrorAnalysis;
}
```

**Backend equivalent** in `backend/services/` uses `httpx` (async).

---

## 13. Environment Variables

```bash
# .env.example
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...            # For Whisper STT + embeddings only
DATABASE_URL=sqlite:///./sprachboot.db
CHROMA_PERSIST_DIR=./chroma_db
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 14. Build Order for Claude Code

### Next Steps (Phase 5 — Polish)
1. Auth (simple email/password — single user app, no multi-tenant needed)
2. B1 engineering vocabulary unlock (Logic to inject `b1_engineering_vocab.json`)
3. TTS (Text-To-Speech for AI Voice Feedback mode)

---

### Implemented Phases

#### Phase 1 — Backend Core (Completed)
1. FastAPI app scaffold + DB models + SQLAlchemy setup
2. `POST /session/turn` — accepts text, calls Llama via OpenRouter, returns response
3. `error_analysis.py` — calls DeepSeek, parses JSON, stores to DB
4. Basic `memory.py` — SQLite reads/writes (no ChromaDB yet)
5. Test: curl a turn, see DB rows appear

#### Phase 2 — Frontend Shell (Completed)
1. Next.js app + Tailwind setup
2. `/speak` page — text input only (no voice yet)
3. Chat bubble UI
4. Wire to `/session/turn` API
5. ErrorOverlay component — shows corrections after each turn
6. Test: full text conversation loop works end to end

#### Phase 3 — Voice + Memory (Completed)
1. Whisper integration (VoiceRecorder.tsx → backend transcription endpoint)
2. ChromaDB setup + embedding pipeline
3. RAG context injection into Llama prompt
4. Profile engine + confidence scoring
5. Test: voice conversation with memory-aware responses

#### Phase 4 — Tests + Analytics (Completed)
1. CEFR test engine (A1 baseline + weekly)
2. `/test` page
3. `/analytics` page with Recharts
4. Weekly report generation
5. Spaced repetition scheduler
6. Learning pattern detection (Month 2 feature stubbed)

---

## 15. Key Implementation Notes for Claude Code

- **Error analysis is a background task** — use `fastapi.BackgroundTasks`. The frontend doesn't wait for it; it polls or receives via a follow-up endpoint.
- **Llama usage** — Keep an eye on credit usage, Llama 70B is paid on OpenRouter. Build a fallback: if rate-limited, switch to `deepseek/deepseek-v4-flash` (same OpenRouter client).
- **ChromaDB in dev** — persist to `./chroma_db/` directory. In prod, consider Qdrant cloud.
- **All German text processing** — lowercase before storing to `word_stats`, but display original.
- **Never store audio** — transcribe immediately, store only the text. Privacy.
- **SM-2 runs daily** — a cron job (APScheduler in FastAPI) that marks words due for review.
- **Test format is LOCKED** — weekly test questions must not randomize between weeks. Same 10 questions, different ordering max. Score comparison requires consistent format.
- **OpenRouter HTTP-Referer** — must be set to a valid URL or OpenRouter may rate-limit free model access.
