from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.db import get_db, Session as DBSession, Turn, WordStat, PatternStat, TestResult
from models.schemas import WeaknessResponse, WeakPattern, ProfileSummary
from services.memory import get_weak_patterns, get_low_confidence_words
from services.profile_engine import estimate_level
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/summary", response_model=ProfileSummary)
async def profile_summary(db: AsyncSession = Depends(get_db)):
    sess_count = await db.scalar(select(func.count()).select_from(DBSession))
    one_week_ago = datetime.now() - timedelta(days=7)
    week_sess_count = await db.scalar(
        select(func.count()).select_from(DBSession).where(DBSession.date >= one_week_ago)
    )
    turn_count = await db.scalar(select(func.count()).select_from(Turn))
    confident = await db.scalar(
        select(func.count()).select_from(WordStat).where(WordStat.confidence >= 0.7)
    )
    learning = await db.scalar(
        select(func.count()).select_from(WordStat).where(WordStat.confidence < 0.7)
    )
    level = await estimate_level(db)

    # V2 accuracy
    v2_result = await db.execute(
        select(PatternStat).where(PatternStat.pattern_key == "V2_violation")
    )
    v2 = v2_result.scalar_one_or_none()
    v2_accuracy = v2.accuracy if v2 else 0.0

    # Latest test score
    latest_test = await db.execute(
        select(TestResult).order_by(TestResult.date.desc()).limit(1)
    )
    test = latest_test.scalar_one_or_none()
    test_score = test.score if test else 0.0

    return ProfileSummary(
        current_level=level,
        total_sessions=sess_count or 0,
        sessions_this_week=week_sess_count or 0,
        total_turns=turn_count or 0,
        streak_days=0,  # Phase 3: implement streak
        words_confident=confident or 0,
        words_learning=learning or 0,
        v2_accuracy=v2_accuracy,
        latest_test_score=test_score,
    )


@router.get("/weaknesses", response_model=WeaknessResponse)
async def profile_weaknesses(db: AsyncSession = Depends(get_db)):
    weak_patterns = await get_weak_patterns(db, limit=5)
    low_conf_words = await get_low_confidence_words(db, limit=10)
    level = await estimate_level(db)

    return WeaknessResponse(
        top_weak_patterns=[
            WeakPattern(
                pattern_key=p["pattern_key"],
                accuracy=p["accuracy"],
                error_count=p["error_count"],
            )
            for p in weak_patterns
        ],
        low_confidence_words=low_conf_words,
        current_level_estimate=level,
        days_to_next_level=42,  # stub — implement in Phase 3
    )
