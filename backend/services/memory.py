"""SQLite memory reads/writes. Phase 1: no ChromaDB (added Phase 3)."""
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models.db import PatternStat, WordStat
from datetime import datetime


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


async def get_low_confidence_words(db: AsyncSession, limit: int = 10) -> List[str]:
    """Return words with confidence < 0.6, ordered by next_review (due first)."""
    result = await db.execute(
        select(WordStat.word)
        .where(WordStat.confidence < 0.6)
        .order_by(WordStat.next_review.asc().nullsfirst())
        .limit(limit)
    )
    return list(result.scalars().all())


