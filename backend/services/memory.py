"""SQLite memory reads — weak patterns, low-confidence words, in-session history."""
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models.db import PatternStat, WordStat, Turn


async def get_weak_patterns(db: AsyncSession, limit: int = 5) -> List[Dict]:
    """Return top weak patterns sorted by error_count descending."""
    result = await db.execute(
        select(PatternStat)
        .where(PatternStat.is_weak == True)  # noqa: E712
        .order_by(desc(PatternStat.error_count))
        .limit(limit)
    )
    patterns = result.scalars().all()
    return [
        {
            "pattern_key": p.pattern_key,
            "accuracy": p.accuracy,
            "error_count": p.error_count,
            "error_type": p.error_type,
        }
        for p in patterns
    ]


async def get_session_history(
    db: AsyncSession,
    session_id: int,
    before_turn_id: int,
    max_turns: int = 10,
) -> List[Dict]:
    """In-session chat history as [{role, content}, ...] for the LLM.

    Prior turns only (id < before_turn_id) with an AI response already set. Uses
    user_raw (what the model actually saw) for the user side. Capped to the last
    `max_turns` exchanges to bound token cost.
    """
    result = await db.execute(
        select(Turn)
        .where(
            Turn.session_id == session_id,
            Turn.id < before_turn_id,
            Turn.ai_response.isnot(None),
            Turn.ai_response != "",
        )
        .order_by(desc(Turn.id))
        .limit(max_turns)
    )
    turns = list(reversed(result.scalars().all()))  # back to chronological
    history: List[Dict] = []
    for t in turns:
        history.append({"role": "user", "content": t.user_raw})
        history.append({"role": "assistant", "content": t.ai_response})
    return history


async def get_low_confidence_words(db: AsyncSession, limit: int = 10) -> List[str]:
    """Return words with confidence < 0.6, ordered by next_review (due first)."""
    result = await db.execute(
        select(WordStat.word)
        .where(WordStat.confidence < 0.6)
        .order_by(WordStat.next_review.asc().nullsfirst())
        .limit(limit)
    )
    return list(result.scalars().all())
