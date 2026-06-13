"""Tests for PR2 — confidence fix, history threading, difficulty controller, scenario."""
import pytest
from models.db import Session as DBSession, Turn
from services.error_analysis import classify_word_uses
from services.difficulty import compute_difficulty
from services.memory import get_session_history
from services.scenario import goals_to_json, goals_from_json, generate_scenario


# ── confidence credit model (pure) ──────────────────────────────────────────────

def test_vocab_error_marks_word_incorrect():
    errors = [{"error_type": "vocab", "user_fragment": "become"}]
    uses = dict(classify_word_uses("ich will become besser", errors))
    assert uses["become"] is False
    assert uses["ich"] is True and uses["besser"] is True


def test_word_order_error_does_not_penalize_words():
    # Arrangement error — the individual words are fine, confidence must not drop.
    errors = [{"error_type": "word_order", "user_fragment": "ich wandern gehe"}]
    uses = dict(classify_word_uses("ich wandern gehe", errors))
    assert all(uses.values())


def test_no_errors_all_correct():
    uses = classify_word_uses("ich gehe nach hause", [])
    assert all(c for _, c in uses) and len(uses) == 4


# ── difficulty controller (pure) ────────────────────────────────────────────────

def test_difficulty_empty_holds():
    assert compute_difficulty([])["band"] == "hold"


def test_difficulty_eases_when_errors_high():
    recent = [{"error_count": 3, "word_count": 8}, {"error_count": 2, "word_count": 7}]
    assert compute_difficulty(recent)["band"] == "ease"


def test_difficulty_stretches_when_safe_and_clean():
    recent = [{"error_count": 0, "word_count": 3}, {"error_count": 0, "word_count": 4}]
    assert compute_difficulty(recent)["band"] == "stretch"


def test_difficulty_holds_in_flow():
    recent = [{"error_count": 1, "word_count": 10}, {"error_count": 0, "word_count": 12}]
    assert compute_difficulty(recent)["band"] == "hold"


def test_difficulty_directive_present():
    d = compute_difficulty([{"error_count": 5, "word_count": 9}])
    assert "DIFFICULTY:" in d["directive"]


# ── scenario goals json (pure) ──────────────────────────────────────────────────

def test_goals_json_roundtrip():
    goals = ["Explain knee pain", "Ask for an appointment", "Say goodbye"]
    assert goals_from_json(goals_to_json(goals)) == goals


def test_goals_from_json_handles_garbage():
    assert goals_from_json(None) == []
    assert goals_from_json("not json") == []


@pytest.mark.asyncio
async def test_generate_scenario_fallback_without_key(monkeypatch):
    import services.openrouter_client as oc
    monkeypatch.setattr(oc, "resolve_api_key", lambda: None)
    s = await generate_scenario("doctor, knee pain, Tuesday")
    assert s["counterpart_role"] and s["opening_line"]
    assert len(s["goals"]) == 3


# ── in-session history threading (DB) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_history_chronological_and_excludes_current(db):
    s = DBSession(mode="chat", topic="daily_life")
    db.add(s)
    await db.flush()
    t1 = Turn(session_id=s.id, user_raw="hallo", ai_response="Hallo!", error_count=0)
    t2 = Turn(session_id=s.id, user_raw="wie geht es", ai_response="Gut!", error_count=0)
    t3 = Turn(session_id=s.id, user_raw="aktuelle frage", ai_response="", error_count=0)  # current, no AI yet
    db.add_all([t1, t2, t3])
    await db.flush()

    hist = await get_session_history(db, s.id, before_turn_id=t3.id)
    assert hist == [
        {"role": "user", "content": "hallo"},
        {"role": "assistant", "content": "Hallo!"},
        {"role": "user", "content": "wie geht es"},
        {"role": "assistant", "content": "Gut!"},
    ]


@pytest.mark.asyncio
async def test_session_history_empty_for_first_turn(db):
    s = DBSession(mode="chat", topic="daily_life")
    db.add(s)
    await db.flush()
    t1 = Turn(session_id=s.id, user_raw="erste", ai_response="", error_count=0)
    db.add(t1)
    await db.flush()
    assert await get_session_history(db, s.id, before_turn_id=t1.id) == []
