from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer, String, Float, Boolean, Text, ForeignKey, DateTime, func
)
from typing import Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


def _resolve_db_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    return "sqlite:///./sprachboot.db"


RAW_URL = _resolve_db_url()
# Convert sqlite:/// → sqlite+aiosqlite:///
if RAW_URL.startswith("sqlite:///"):
    ASYNC_URL = RAW_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
else:
    ASYNC_URL = RAW_URL

engine = create_async_engine(ASYNC_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    duration_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="chat")  # 'voice' | 'chat'
    topic: Mapped[str] = mapped_column(String(50), default="daily_life")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scenario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("scenarios.id"), nullable=True
    )
    goals_hit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON [{goal,hit}]

    turns: Mapped[List["Turn"]] = relationship("Turn", back_populates="session")


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user_raw: Mapped[str] = mapped_column(Text)
    user_corrected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_response: Mapped[str] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    had_english_switch: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["Session"] = relationship("Session", back_populates="turns")
    errors: Mapped[List["Error"]] = relationship("Error", back_populates="turn")


class Error(Base):
    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    turn_id: Mapped[int] = mapped_column(Integer, ForeignKey("turns.id"))
    error_type: Mapped[str] = mapped_column(String(50))
    pattern_key: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(10))
    user_fragment: Mapped[str] = mapped_column(Text)
    correct_form: Mapped[str] = mapped_column(Text)
    rule_shown: Mapped[bool] = mapped_column(Boolean, default=False)

    turn: Mapped["Turn"] = relationship("Turn", back_populates="errors")


class WordStat(Base):
    __tablename__ = "word_stats"

    word: Mapped[str] = mapped_column(String(200), primary_key=True)
    total_uses: Mapped[int] = mapped_column(Integer, default=0)
    correct_uses: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cefr_level: Mapped[str] = mapped_column(String(5), default="A1")
    next_review: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)


class PatternStat(Base):
    __tablename__ = "pattern_stats"

    pattern_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    error_type: Mapped[str] = mapped_column(String(50), default="")
    total_seen: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    last_error: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_weak: Mapped[bool] = mapped_column(Boolean, default=False)


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    test_type: Mapped[str] = mapped_column(String(20))
    cefr_level: Mapped[str] = mapped_column(String(5))
    score: Mapped[float] = mapped_column(Float)
    sections: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    situation: Mapped[str] = mapped_column(Text)            # raw user declaration
    title: Mapped[str] = mapped_column(String(120), default="")
    counterpart_role: Mapped[str] = mapped_column(String(80), default="")  # who AI plays
    opening_line: Mapped[str] = mapped_column(Text, default="")            # AI's first line
    goals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # JSON list
    topic: Mapped[str] = mapped_column(String(50), default="scenario")
    status: Mapped[str] = mapped_column(String(20), default="active")      # 'active'|'archived'
    # Transfer loop: rehearse → do it for real → report back.
    transfer_status: Mapped[str] = mapped_column(String(20), default="none")  # 'none'|'pending'|'reported'
    transfer_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_practiced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    user_name: Mapped[str] = mapped_column(String(100), default="User")
    conv_model: Mapped[str] = mapped_column(
        String(200), default="meta-llama/llama-3.3-70b-instruct"
    )
    analysis_model: Mapped[str] = mapped_column(
        String(200), default="deepseek/deepseek-v4-flash"
    )
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)


async def _ensure_columns(conn):
    """Lightweight idempotent migration — create_all does not ALTER existing tables.

    Adds columns introduced after a table was first created. SQLite supports
    ADD COLUMN; each add is guarded by a PRAGMA check so it is safe to re-run.
    """
    from sqlalchemy import text
    # (table, column, DDL type)
    wanted = [
        ("sessions", "scenario_id", "INTEGER"),
        ("sessions", "goals_hit", "TEXT"),
        ("scenarios", "transfer_status", "VARCHAR(20) DEFAULT 'none'"),
        ("scenarios", "transfer_report", "TEXT"),
        ("scenarios", "last_practiced_at", "DATETIME"),
    ]
    for table, column, coltype in wanted:
        rows = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
        existing = {r[1] for r in rows.fetchall()}
        if column not in existing:
            await conn.exec_driver_sql(
                f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"
            )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_columns(conn)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        yield session


async def get_or_create_preferences(session: AsyncSession) -> "UserPreferences":
    from sqlalchemy import select
    result = await session.execute(
        select(UserPreferences).where(UserPreferences.id == 1)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = UserPreferences(id=1)
        session.add(prefs)
        await session.commit()
        await session.refresh(prefs)
    return prefs
