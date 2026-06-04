from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from models.db import get_db, Session as DBSession, TestResult, WordStat, PatternStat
from models.schemas import WeeklyAnalytics

router = APIRouter()

@router.get("/dashboard", response_model=WeeklyAnalytics)
async def get_analytics_dashboard(db: AsyncSession = Depends(get_db)):
    one_week_ago = datetime.now() - timedelta(days=7)
    
    # 1. Sessions this week
    sessions_this_week = await db.scalar(
        select(func.count()).select_from(DBSession).where(DBSession.date >= one_week_ago)
    )
    
    # 2. Total minutes
    total_duration = await db.scalar(
        select(func.sum(DBSession.duration_s)).where(DBSession.date >= one_week_ago)
    )
    total_minutes = (total_duration or 0) // 60
    
    # 3. Turns total
    turns_total = await db.scalar(
        select(func.sum(DBSession.turn_count)).where(DBSession.date >= one_week_ago)
    )
    
    # 4. Error rate trend (mocked for now, would typically aggregate errors over last N weeks)
    error_rate_trend = [0.75, 0.70, 0.65, 0.62, 0.58, 0.55]
    
    # 5. Best day
    # Group by weekday
    best_day = "Wednesday" # Mock
    
    # 6. Patterns
    improving = await db.scalars(
        select(PatternStat.pattern_key).order_by(desc(PatternStat.accuracy)).limit(2)
    )
    regressing = await db.scalars(
        select(PatternStat.pattern_key).order_by(PatternStat.accuracy).limit(2)
    )
    
    # 7. Words added
    words_added = await db.scalar(
        select(func.count()).select_from(WordStat)
        .where(WordStat.confidence >= 0.7)
        .where(WordStat.last_seen >= one_week_ago)
    )
    
    # 8. Test scores trend over time
    tests = await db.scalars(
        select(TestResult).order_by(TestResult.date)
    )
    
    return WeeklyAnalytics(
        week=f"{datetime.now().year}-W{datetime.now().isocalendar()[1]}",
        sessions=sessions_this_week or 0,
        total_minutes=total_minutes,
        turns_total=turns_total or 0,
        error_rate_trend=error_rate_trend,
        best_day=best_day,
        pattern_improvements=list(improving.all()),
        pattern_regressions=list(regressing.all()),
        words_added_to_confident=words_added or 0
    )
