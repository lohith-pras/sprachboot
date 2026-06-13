"""Tests for the Growth Receipt (PR1): scoring honesty + receipt assembly."""
import pytest
from models.db import Session as DBSession, Turn, Error
from services.receipt import (
    compute_overall_score,
    recompute_session_score,
    build_receipt,
    W_ACC,
    W_REACH,
)


# ── compute_overall_score (pure) ────────────────────────────────────────────────

def test_zero_turns_returns_none():
    assert compute_overall_score([]) is None


def test_score_is_bounded_0_1():
    # Garbage: long, rare-word-spammy, all high errors → reach high, accuracy floored.
    turns = [
        {"corrected": " ".join(f"wort{i}" for i in range(30)),
         "severities": ["high"] * 10}
        for _ in range(5)
    ]
    s = compute_overall_score(turns)
    assert 0.0 <= s <= 1.0


def test_retreating_to_safe_short_sentences_does_not_win():
    # Both error-free. Reach term must make the complex attempt outscore the safe one.
    safe = [{"corrected": "Ja gut.", "severities": []} for _ in range(4)]
    reaching = [
        {"corrected": "Ich glaube, dass die Reichweite des Fahrzeugs zu klein ist, "
                      "weil der Akku noch lädt.", "severities": []}
        for _ in range(4)
    ]
    assert compute_overall_score(reaching) > compute_overall_score(safe)


def test_errors_lower_accuracy():
    clean = [{"corrected": "Ich gehe heute in die Stadt einkaufen.", "severities": []}]
    dirty = [{"corrected": "Ich gehe heute in die Stadt einkaufen.",
              "severities": ["high", "high", "high"]}]
    assert compute_overall_score(clean) > compute_overall_score(dirty)


def test_severity_weighting():
    one_high = [{"corrected": "Ich gehe nach Hause.", "severities": ["high"]}]
    one_low = [{"corrected": "Ich gehe nach Hause.", "severities": ["low"]}]
    assert compute_overall_score(one_low) > compute_overall_score(one_high)


def test_weights_sum_to_one():
    assert W_ACC + W_REACH == pytest.approx(1.0)


# ── recompute_session_score (DB) ────────────────────────────────────────────────

async def _make_session(db, topic="daily_life", score=None):
    s = DBSession(mode="chat", topic=topic, turn_count=0, overall_score=score)
    db.add(s)
    await db.flush()
    return s


async def _add_turn(db, session_id, corrected, severities=()):
    t = Turn(session_id=session_id, user_raw=corrected, user_corrected=corrected,
             ai_response="ok", error_count=len(severities))
    db.add(t)
    await db.flush()
    for sev in severities:
        db.add(Error(turn_id=t.id, error_type="x", pattern_key="x",
                     severity=sev, user_fragment="a", correct_form="b"))
    await db.flush()
    return t


@pytest.mark.asyncio
async def test_recompute_persists_score(db):
    s = await _make_session(db)
    await _add_turn(db, s.id, "Ich glaube, dass das Wetter heute schön ist.")
    await db.commit()
    score = await recompute_session_score(db, s.id)
    assert score is not None and 0.0 <= score <= 1.0
    refreshed = await db.get(DBSession, s.id)
    assert refreshed.overall_score == score


@pytest.mark.asyncio
async def test_recompute_zero_turn_session_is_none(db):
    s = await _make_session(db)
    await db.commit()
    score = await recompute_session_score(db, s.id)
    assert score is None


# ── build_receipt (DB) ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_receipt_baseline_when_few_priors(db):
    s = await _make_session(db)
    await _add_turn(db, s.id, "Hallo, wie geht es dir?")
    await db.commit()
    await recompute_session_score(db, s.id)
    r = await build_receipt(db, s.id)
    assert r["is_baseline"] is True
    assert r["delta"] is None
    assert r["prior_session_count"] == 0


@pytest.mark.asyncio
async def test_receipt_delta_same_topic_excludes_null_and_other_topic(db):
    # Two scored same-topic priors → trailing avg + delta.
    await _make_session(db, topic="daily_life", score=0.4)
    await _make_session(db, topic="daily_life", score=0.6)
    # Noise that must be excluded:
    await _make_session(db, topic="daily_life", score=None)   # NULL excluded
    await _make_session(db, topic="uni", score=0.9)           # other topic excluded
    current = await _make_session(db, topic="daily_life", score=0.8)
    await db.commit()

    r = await build_receipt(db, current.id)
    assert r["is_baseline"] is False
    assert r["prior_session_count"] == 2
    assert r["trailing_avg"] == pytest.approx(0.5)
    assert r["delta"] == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_receipt_foregrounds_corrected(db):
    s = await _make_session(db)
    t = Turn(session_id=s.id, user_raw="ich gehen haus",
             user_corrected="Ich gehe nach Hause.", ai_response="Schön!", error_count=1)
    db.add(t)
    await db.commit()
    r = await build_receipt(db, s.id)
    assert r["replay"][0]["user_corrected"] == "Ich gehe nach Hause."
    assert r["replay"][0]["user_raw"] == "ich gehen haus"


@pytest.mark.asyncio
async def test_receipt_missing_session_returns_none(db):
    assert await build_receipt(db, 9999) is None
