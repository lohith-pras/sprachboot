# TODOS

## Fix word_stats confidence credit model (always 1.0)

**What:** `persist_analysis` in [error_analysis.py:132-153](backend/services/error_analysis.py:132) only
writes words from the *corrected* sentence and always increments both `total_uses` and `correct_uses`.
There is no code path that increments `total_uses` without `correct_uses`, so
`confidence = correct_uses / total_uses` is **always 1.0** for every word ever seen.

**Why it matters:**
- `get_low_confidence_words` filters `confidence < 0.6` ([memory.py:33](backend/services/memory.py:33))
  → always returns empty → the "weave in low-confidence words" feature is silently dead.
- SM-2 due-word surfacing never fires (no word is ever low-confidence).
- Honest vocabulary-confidence growth is impossible to show in the Growth Receipt until this is fixed.
  (PR1 works around it by using error-rate / turns-sustained / distinct-vocab as the honest signals.)

**How to fix (sketch):** in `persist_analysis`, also tokenize the *raw* user sentence, align raw vs
corrected, and for words that were used wrong (appear in an error's `user_fragment`, or differ from the
corrected form) increment `total_uses` WITHOUT `correct_uses`. Then confidence can actually move.

**Pros:** revives low_conf_words + SM-2 spaced repetition; unlocks real vocab-confidence as a receipt signal.
**Cons:** needs raw-vs-corrected word-alignment logic; touches the core learning loop; test carefully.
**Depends on / blocked by:** none. Independent of PR1 (Growth Receipt). Do before any vocab-confidence
feature in the receipt or analytics.

**Context:** surfaced during /plan-eng-review of the Growth Receipt (feat/growth-receipt, 2026-06-12).
Deferred from PR1 deliberately — the receipt uses honest signals that don't depend on this field.
