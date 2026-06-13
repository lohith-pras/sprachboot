"""Tests for PR3 — scenario goal scoring + transfer-loop receipt extras."""
import pytest
from models.db import Session as DBSession, Scenario
from services.goal_scoring import (
    score_goals,
    score_goals_fallback,
    goals_hit_to_json,
    goals_hit_from_json,
)
from services.scenario import goals_to_json
from services.receipt import build_receipt


# ── goal scoring (pure / no-network) ────────────────────────────────────────────

def test_goals_hit_json_roundtrip():
    results = [{"goal": "Greet", "hit": True}, {"goal": "Pay", "hit": False}]
    assert goals_hit_from_json(goals_hit_to_json(results)) == results


def test_goals_hit_from_json_garbage():
    assert goals_hit_from_json(None) == []
    assert goals_hit_from_json("nope") == []


def test_score_goals_fallback_shape():
    fb = score_goals_fallback(["a", "b"])
    assert fb == [{"goal": "a", "hit": False}, {"goal": "b", "hit": False}]


@pytest.mark.asyncio
async def test_score_goals_empty_goals():
    assert await score_goals("situation", [], "transcript", "model") == []


@pytest.mark.asyncio
async def test_score_goals_no_key_falls_back(monkeypatch):
    import services.openrouter_client as oc
    monkeypatch.setattr(oc, "resolve_api_key", lambda: "k")  # key present...
    # ...but empty transcript → still fallback (nothing to judge)
    res = await score_goals("doctor", ["Explain pain"], "   ", "model")
    assert res == [{"goal": "Explain pain", "hit": False}]


# ── scenario-aware receipt (DB) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_receipt_includes_scenario_and_goals(db):
    sc = Scenario(
        situation="doctor, knee pain, Tuesday",
        title="Doctor visit",
        counterpart_role="Hausärztin",
        opening_line="Guten Tag!",
        goals=goals_to_json(["Explain knee pain", "Ask for appointment", "Say goodbye"]),
    )
    db.add(sc)
    await db.flush()

    s = DBSession(mode="chat", topic=f"scenario:{sc.id}", scenario_id=sc.id)
    s.goals_hit = goals_hit_to_json([
        {"goal": "Explain knee pain", "hit": True},
        {"goal": "Ask for appointment", "hit": True},
        {"goal": "Say goodbye", "hit": False},
    ])
    db.add(s)
    await db.commit()

    r = await build_receipt(db, s.id)
    assert r["scenario_title"] == "Doctor visit"
    assert r["counterpart_role"] == "Hausärztin"
    assert [g["hit"] for g in r["goals"]] == [True, True, False]


@pytest.mark.asyncio
async def test_receipt_non_scenario_has_no_goals(db):
    s = DBSession(mode="chat", topic="daily_life")
    db.add(s)
    await db.commit()
    r = await build_receipt(db, s.id)
    assert r["scenario_title"] is None
    assert r["goals"] == []
