# Spec B — DeepL Translation, Daily Log & Content Discovery

> **Branch:** future (`feat/learning-layer` or similar) — planned now, built after Spec A
> **Date:** 2026-06-05
> **Status:** Approved design, ready for implementation plan
> **Scope:** Group 2 of the SprachBoot development roadmap (features 3 + 4 + 5)

---

## 0. Goal

Add a learning-support layer on top of the existing conversation/test/analytics loop:

1. **DeepL translation** — inline word lookup + per-message "show in English".
2. **Daily log** — per-day record of words encountered, sentences gotten right,
   mistakes made, and an AI-written focus diagnosis of *why* the mistakes happen
   (grammar vs vocab vs sentence structure).
3. **Content discovery** — on-demand web resources targeting the user's weak areas
   (Firecrawl), plus dashboard engagement cards: word of the day + persona-based
   German articles/podcasts the user would actually enjoy.

The driving principle from the user: *"whatever mistakes I do, I shouldn't repeat
them again at least 2–3 times in the same week"* — so the system diagnoses
weaknesses from real chat/error data and points to targeted material.

**Non-goals (documented as future):**
- DeepL translation of error-overlay corrections (feature 3C) — future update.
- Daily automatic content digest / background jobs (feature 4B) — future; on-demand only for now.

---

## 1. Context

Depends on Spec A landing first:
- Keyring infrastructure (`KEYRING_SERVICE = "SprachBoot"`) — DeepL key reuses it.
- `user_preferences` table exists.
- Existing tables: `turns`, `errors`, `word_stats`, `pattern_stats` provide all the
  raw data the daily log and weakness detection read from.

---

## 2. Database

Two new tables.

```sql
CREATE TABLE daily_content (
    date          TEXT PRIMARY KEY,   -- 'YYYY-MM-DD'
    wotd_word     TEXT,               -- word of the day (German)
    wotd_meaning  TEXT,               -- English meaning
    wotd_example  TEXT,               -- example sentence
    persona_json  TEXT                -- cached user-interest persona for this day
);

CREATE TABLE discovered_resources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    kind        TEXT,    -- 'weakness' | 'engagement'
    title       TEXT,
    url         TEXT,
    summary     TEXT,
    pattern_key TEXT     -- nullable; set for weakness-targeted resources
);
```

DeepL API key stored via `keyring.set_password("SprachBoot", "deepl", key)`.
Added to onboarding Step 2 + settings page as an optional third key field (Spec A).

---

## 3. DeepL translation (features 3A + 3B)

### Backend — `backend/services/translation.py`

- Wraps the `deepl` Python lib (add to `pyproject.toml`).
- `translate_word(word: str) -> str | None`
- `translate_sentence(text: str) -> str | None`
- Reads key from keyring; if missing returns `None` so the frontend hides the
  translate UI gracefully.
- In-memory LRU cache (words repeat heavily).

### Backend — `backend/routers/translate.py`

- `POST /translate/word` → `{word}` → `{translation}`
- `POST /translate/sentence` → `{text}` → `{translation}`

### Frontend

- `ChatBubble.tsx` — each word wrapped in a clickable span. Click → debounced
  `/translate/word` → tooltip popover with the English meaning.
- Per AI bubble — "Show in English" toggle → `/translate/sentence` → renders
  translation under the original, cached in component state.

Feature 3C (translate error-overlay `correct_form`/`rule`) — **out of scope**, future.

---

## 4. Daily Log (`/log` page)

### Backend — `GET /analytics/daily-log?date=YYYY-MM-DD`

Queries existing `turns`, `errors`, `word_stats` for that date. Returns:

```json
{
  "date": "2026-06-05",
  "session_count": 2,
  "words_encountered": ["wandern", "Nähe"],
  "correct_sentences": ["Ich gehe wandern."],
  "mistakes": [
    {"user_fragment": "ich wandern gehe",
     "correct_form": "ich gehe wandern",
     "pattern_key": "V2_violation"}
  ],
  "top_patterns": [{"pattern_key": "V2_violation", "count": 4}],
  "focus_diagnosis": "..."
}
```

- `focus_diagnosis`: DeepSeek analyzes the day's top weak patterns + sample
  mistakes and writes ~2 sentences — root cause classification (grammar vs vocab
  vs sentence structure) + what to drill. Generated on request, cached per-date
  in memory.

### Frontend — `/log` page

- Date picker (defaults to today).
- Sections: Sessions summary · Words encountered · Sentences you got right ·
  Mistakes (with corrections) · **Focus area** card (the AI diagnosis).
- Focus card has a "Find resources to fix this" button → triggers Section 5
  weakness discovery.

---

## 5. Weakness Content Discovery (on-demand, Firecrawl)

### Backend — `POST /analytics/weaknesses/resources`

- Body: `{pattern_keys: [...]}` (top 2–3 weak patterns).
- Maps each `pattern_key` → a search query
  (e.g. `V2_violation` → "German verb position V2 rule explained beginner").
- Calls the Firecrawl `search` API; returns 2–3 `{title, url, summary}` per pattern.
- Stores results in `discovered_resources` with `kind='weakness'` and the
  `pattern_key`.
- Triggered by button only — **no background job**. Feature 4B (daily auto-digest)
  documented as future.

### Frontend

- Results render as cards under the Focus area on `/log`.

---

## 6. Dashboard cards — WOTD + Engagement (feature 5, Firecrawl)

### Word of the Day — `GET /content/wotd`

- If a `daily_content` row exists for today → return it.
- Else: pick a word from `word_stats` in the "learning" zone (confidence ~0.3–0.7,
  not yet confident), DeepSeek generates meaning + example, store in
  `daily_content`, return.
- Same word all day (table-cached); a new word the next day.

### Engagement content — `GET /content/discover`

- Build a persona from the last ~20 `user_raw` turns (DeepSeek extracts interest
  topics, e.g. "EV engineering, hiking, cooking").
- Firecrawl searches for German articles/podcasts on those topics at beginner
  level.
- Return 1–2 resource cards, store with `kind='engagement'`, cache per-day in
  `daily_content.persona_json` + `discovered_resources`.

### Frontend

- WOTD card + engagement cards added to the dashboard bento grid in `page.tsx`.

---

## 7. Build order

1. DeepL service + endpoints + `ChatBubble` integration (independent).
2. Daily log endpoint + `/log` page.
3. Firecrawl weakness resources (builds on #2).
4. WOTD card (independent).
5. Persona engagement cards (builds on persona extraction).

---

## 8. Open risks

- **Firecrawl result quality** — search results for grammar topics may be noisy;
  may need query tuning + result filtering/ranking.
- **DeepSeek persona drift** — persona from only 20 turns may be thin early on;
  acceptable, improves with usage.
- **DeepL free-tier quota** — word-hover can generate many calls; LRU cache +
  debounce mitigate, but monitor usage.
