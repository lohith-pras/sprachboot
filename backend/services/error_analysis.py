"""Calls DeepSeek V4 Flash to analyze grammar errors. Runs synchronously before conversation."""
import json
from datetime import datetime, timedelta
from typing import List
from models.db import AsyncSessionLocal, Turn, Error, WordStat, PatternStat
from services.openrouter_client import call_openrouter, DEEPSEEK_MODEL
from services.spaced_repetition import update_interval
from sqlalchemy import select

ANALYSIS_PROMPT = """\
You are a German language error analyzer. The learner said:
"{user_raw}"

Analyze the learner's sentence and return ONLY valid JSON in this exact schema:
{{
  "corrected": "string — the corrected German sentence",
  "errors": [
    {{
      "error_type": "word_order|gender|case|verb_form|vocab|capitalisation|false_friend",
      "pattern_key": "short_snake_case_key",
      "severity": "high|medium|low",
      "user_fragment": "what the user said",
      "correct_form": "what it should be",
      "rule": "one-sentence grammar rule — only for high severity"
    }}
  ]
}}

RULES:
- Return ONLY JSON. No preamble, no markdown backticks.
- If no errors, return {{"corrected": "{user_raw}", "errors": []}}
- Severity guide: high = breaks comprehension or sounds very wrong,
  medium = grammatically incorrect but understandable, low = style/preference
- pattern_key examples: V2_violation, verb_final_subordinate,
  accusative_after_durch, noun_not_capitalised, false_friend_gift,
  gender_article_wrong, dativ_after_mit
- IMPORTANT: Completely ignore noun capitalization. Do NOT flag missing capitalization as an error.
- IMPORTANT: Do NOT create an error if the user_fragment is identical to the correct_form.
"""


async def analyze_errors(user_raw: str) -> dict:
    """Call DeepSeek and return {corrected, errors[]}. No DB writes."""
    from services.openrouter_client import resolve_api_key
    from models.db import AsyncSessionLocal as _ASL, get_or_create_preferences
    if not resolve_api_key():
        return {"corrected": user_raw, "errors": []}

    async with _ASL() as _pdb:
        _prefs = await get_or_create_preferences(_pdb)
        analysis_model = _prefs.analysis_model

    prompt = ANALYSIS_PROMPT.format(user_raw=user_raw)

    try:
        raw_content = await call_openrouter(
            analysis_model,
            [{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(raw_content) if raw_content else {"corrected": user_raw, "errors": []}
    except Exception as e:
        print(f"[error_analysis] DeepSeek call failed: {e}")
        return {"corrected": user_raw, "errors": []}


async def persist_analysis(
    turn_id: int,
    analysis: dict,
    previously_weak_pattern_keys: List[str] | None = None,
):
    """Write analysis results to DB. Also credits success on previously-weak patterns."""
    corrected = analysis.get("corrected", "")
    errors = analysis.get("errors", [])
    error_keys = {e.get("pattern_key") for e in errors}

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Turn).where(Turn.id == turn_id))
        turn = result.scalar_one_or_none()
        if turn:
            turn.user_corrected = corrected
            turn.error_count = len(errors)

        # Insert errors + update pattern_stats for each error
        for err in errors:
            db_error = Error(
                turn_id=turn_id,
                error_type=err.get("error_type", "unknown"),
                pattern_key=err.get("pattern_key", "unknown"),
                severity=err.get("severity", "low"),
                user_fragment=err.get("user_fragment", ""),
                correct_form=err.get("correct_form", ""),
                rule_shown=err.get("severity") == "high",
            )
            db.add(db_error)

            pk = err.get("pattern_key", "unknown")
            pat_result = await db.execute(
                select(PatternStat).where(PatternStat.pattern_key == pk)
            )
            pat = pat_result.scalar_one_or_none()
            if pat is None:
                pat = PatternStat(
                    pattern_key=pk,
                    error_type=err.get("error_type", "unknown"),
                )
                db.add(pat)
            pat.total_seen = (pat.total_seen or 0) + 1
            pat.error_count = (pat.error_count or 0) + 1
            pat.last_error = datetime.now()
            pat.accuracy = 1.0 - (pat.error_count / pat.total_seen)
            pat.is_weak = pat.error_count >= 3 and pat.accuracy < 0.60

        # Credit success: previously-weak patterns not in this turn's errors
        if previously_weak_pattern_keys:
            for pk in previously_weak_pattern_keys:
                if pk in error_keys:
                    continue  # already handled above as an error
                pat_result = await db.execute(
                    select(PatternStat).where(PatternStat.pattern_key == pk)
                )
                pat = pat_result.scalar_one_or_none()
                if pat is None:
                    continue
                pat.total_seen = (pat.total_seen or 0) + 1
                # error_count unchanged — this was a correct use
                pat.accuracy = 1.0 - (pat.error_count / pat.total_seen)
                pat.is_weak = pat.error_count >= 3 and pat.accuracy < 0.60

        # Upsert word_stats for every word in the corrected sentence
        words = [
            w.strip(".,!?;:\"'()").lower()
            for w in corrected.split()
            if len(w) > 1
        ]
        for word in words:
            w_result = await db.execute(
                select(WordStat).where(WordStat.word == word)
            )
            ws = w_result.scalar_one_or_none()
            if ws is None:
                ws = WordStat(word=word)
                db.add(ws)
            ws.total_uses = (ws.total_uses or 0) + 1
            ws.correct_uses = (ws.correct_uses or 0) + 1
            ws.last_seen = datetime.now()
            base = ws.correct_uses / max(ws.total_uses, 1)
            ws.confidence = round(base, 3)
            new_interval = update_interval(ws.interval_days or 1, was_correct=True)
            ws.interval_days = new_interval
            ws.next_review = datetime.now() + timedelta(days=new_interval)

        await db.commit()


async def analyze_errors_background(turn_id: int, user_raw: str, ai_response: str):
    """Legacy wrapper — kept for any callers that still use it."""
    analysis = await analyze_errors(user_raw)
    await persist_analysis(turn_id, analysis)
