"""Confidence scoring and CEFR level estimation."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.db import PatternStat, WordStat, TestResult



async def estimate_level(db: AsyncSession) -> str:
    """
    Estimates CEFR level from pattern accuracy + word confidence + test results.
    Returns: 'A1' | 'A1+' | 'A2' | 'A2+' | 'B1'
    """
    # V2 accuracy
    v2_result = await db.execute(
        select(PatternStat).where(PatternStat.pattern_key == "V2_violation")
    )
    v2 = v2_result.scalar_one_or_none()
    v2_accuracy = v2.accuracy if v2 else 0.0

    # Confident words (confidence >= 0.7)
    confident_count = await db.scalar(
        select(func.count()).select_from(WordStat).where(WordStat.confidence >= 0.7)
    ) or 0

    # Latest test score
    latest_test = await db.execute(
        select(TestResult).order_by(TestResult.date.desc()).limit(1)
    )
    test = latest_test.scalar_one_or_none()
    test_score = test.score if test else 0.0

    # Level rules from CLAUDE.md §5d
    if v2_accuracy > 0.80 and confident_count >= 600:
        return "B1"
    elif v2_accuracy > 0.65 and confident_count >= 200:
        return "A2" if test_score < 0.75 else "A2+"
    elif v2_accuracy > 0.50 or confident_count >= 50:
        return "A1+"
    else:
        return "A1"
