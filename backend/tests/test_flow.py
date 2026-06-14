"""Tests for the visible flow dial (Approach C) — flow-zone aggregation in the receipt."""
import pytest
from models.db import Session as DBSession, Turn
from services.receipt import build_receipt


async def _session_with_bands(db, bands):
    s = DBSession(mode="chat", topic="daily_life")
    db.add(s)
    await db.flush()
    for i, b in enumerate(bands):
        db.add(Turn(session_id=s.id, user_raw=f"satz {i}", user_corrected=f"Satz {i}.",
                    ai_response="ok", error_count=0, flow_band=b))
    await db.commit()
    return s


@pytest.mark.asyncio
async def test_flow_zone_pct_counts_hold_share(db):
    s = await _session_with_bands(db, ["hold", "hold", "ease", "stretch"])
    r = await build_receipt(db, s.id)
    assert r["flow_zone_pct"] == pytest.approx(0.5)  # 2 of 4 in flow
    assert r["flow_timeline"] == ["hold", "hold", "ease", "stretch"]


@pytest.mark.asyncio
async def test_flow_zone_excludes_unscored_turns(db):
    s = await _session_with_bands(db, ["hold", None, "hold"])
    r = await build_receipt(db, s.id)
    # None band excluded → 2 scored turns, both hold → 1.0
    assert r["flow_zone_pct"] == pytest.approx(1.0)
    assert r["flow_timeline"] == ["hold", "hold"]


@pytest.mark.asyncio
async def test_flow_zone_none_when_no_bands(db):
    s = await _session_with_bands(db, [None, None])
    r = await build_receipt(db, s.id)
    assert r["flow_zone_pct"] is None
    assert r["flow_timeline"] == []
