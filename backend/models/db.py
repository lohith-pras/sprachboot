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

RAW_URL = os.getenv("DATABASE_URL", "sqlite:///./sprachboot.db")
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


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        yield session
