"""Calls DeepSeek V4 Flash to analyze grammar errors. Runs as a FastAPI BackgroundTask."""
import os
import json
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
from models.db import AsyncSessionLocal, Turn, Error, WordStat, PatternStat
from services.spaced_repetition import update_interval
from sqlalchemy import select

load_dotenv()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"

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


async def analyze_errors_background(turn_id: int, user_raw: str, ai_response: str):
    """Background task: call DeepSeek, parse errors, update all DB tables."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return

    prompt = ANALYSIS_PROMPT.format(user_raw=user_raw)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://sprachboot.vercel.app",
                    "X-Title": "SprachBoot",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"].get("content")
            if not raw_content:
                analysis = {"corrected": user_raw, "errors": []}
            else:
                analysis = json.loads(raw_content)
    except Exception as e:
        print(f"[error_analysis] DeepSeek call failed for turn {turn_id}: {e}")
        return

    corrected = analysis.get("corrected", user_raw)
    errors = analysis.get("errors", [])

    async with AsyncSessionLocal() as db:
        # Update the turn record
        result = await db.execute(select(Turn).where(Turn.id == turn_id))
        turn = result.scalar_one_or_none()
        if turn:
            turn.user_corrected = corrected
            turn.error_count = len(errors)

        # Insert errors + update pattern_stats
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

            # Upsert pattern_stats
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
            # SM-2 update
            new_interval = update_interval(ws.interval_days or 1, was_correct=True)
            ws.interval_days = new_interval
            ws.next_review = datetime.now() + timedelta(days=new_interval)

        await db.commit()
