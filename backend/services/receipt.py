"""Growth Receipt (PR1): honest per-session scoring + receipt assembly.

    overall_score = W_ACC * accuracy + W_REACH * reach     (both in [0,1] → score in [0,1])

ACCURACY rewards correctness. Errors are severity-weighted into a per-turn "load",
normalized against a cap so a few low-severity errors barely dent the score while many
high-severity errors floor it.

REACH rewards *attempting* harder language so a learner cannot win the score by retreating
to short, safe, error-free sentences. Three sub-terms — sentence length, distinct-vocab
range, and complex-structure attempts — each normalized and capped to [0,1], then averaged.

Weights (W_ACC=0.6, W_REACH=0.4): accuracy is primary, but reach is heavy enough that
playing it safe costs more than it saves. Every term is capped to [0,1], so no single
term can run away — e.g. spamming rare words in broken sentences caps reach at 1.0 while
accuracy collapses, netting a low score.

The score is PROVISIONAL until PR2's closed-loop difficulty controller makes signals
comparable across sessions. The delta on a receipt is scoped to prior sessions with the
SAME topic (NULL scores excluded) so the comparison is interpretable and PR2's scenario
grouping inherits a clean, topic-tagged history.
"""
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.db import Session as DBSession, Turn, Error

# ── Score weights / normalization caps (documented above) ───────────────────────
SEVERITY_WEIGHT: Dict[str, float] = {"high": 1.0, "medium": 0.6, "low": 0.3}
ERROR_LOAD_CAP = 2.0    # severity-weighted errors/turn that floors accuracy to 0
W_TARGET = 12.0         # words/turn for full sentence-complexity credit
V_TARGET = 40.0         # distinct words across session for full vocab-reach credit
S_TARGET = 0.5          # complex-structure attempts/turn for full structure credit
W_ACC = 0.6
W_REACH = 0.4

# Subordinating conjunctions — their presence signals an *attempt* at a complex clause.
SUBORDINATORS = {
    "weil", "dass", "ob", "wenn", "obwohl", "damit", "während", "bevor",
    "nachdem", "als", "seit", "sodass", "falls", "indem", "bis", "sobald",
}


def _tokens(text: str) -> List[str]:
    out = []
    for w in (text or "").split():
        t = w.strip(".,!?;:\"'()«»„“”-").lower()
        if t:
            out.append(t)
    return out


def compute_overall_score(turns: List[Dict]) -> Optional[float]:
    """Pure scoring function.

    turns: list of {"corrected": str, "severities": [str, ...]}.
    Returns float in [0,1], or None when there are no turns (no signal to score).
    """
    n = len(turns)
    if n == 0:
        return None

    # ── ACCURACY ──
    total_load = 0.0
    for t in turns:
        for sev in t.get("severities", []) or []:
            total_load += SEVERITY_WEIGHT.get(sev, SEVERITY_WEIGHT["low"])
    load_per_turn = total_load / n
    accuracy = max(0.0, 1.0 - load_per_turn / ERROR_LOAD_CAP)

    # ── REACH ──
    distinct = set()
    total_words = 0
    structure_hits = 0
    for t in turns:
        toks = _tokens(t.get("corrected") or "")
        total_words += len(toks)
        distinct.update(toks)
        structure_hits += sum(1 for w in toks if w in SUBORDINATORS)

    complexity = min(1.0, (total_words / n) / W_TARGET)
    vocab = min(1.0, len(distinct) / V_TARGET)
    structure = min(1.0, (structure_hits / n) / S_TARGET)
    reach = (complexity + vocab + structure) / 3.0

    score = W_ACC * accuracy + W_REACH * reach
    return round(min(1.0, max(0.0, score)), 4)


async def _load_turn_data(db: AsyncSession, session_id: int) -> List[Dict]:
    """Load a session's turns + severities in two queries (no N+1)."""
    turns = (
        await db.execute(
            select(Turn).where(Turn.session_id == session_id).order_by(Turn.id)
        )
    ).scalars().all()
    if not turns:
        return []
    turn_ids = [t.id for t in turns]
    rows = (
        await db.execute(
            select(Error.turn_id, Error.severity).where(Error.turn_id.in_(turn_ids))
        )
    ).all()
    sev_by_turn: Dict[int, List[str]] = {}
    for tid, sev in rows:
        sev_by_turn.setdefault(tid, []).append(sev)
    return [
        {
            "id": t.id,
            "corrected": t.user_corrected or t.user_raw,
            "raw": t.user_raw,
            "ai_response": t.ai_response,
            "error_count": t.error_count or 0,
            "severities": sev_by_turn.get(t.id, []),
        }
        for t in turns
    ]


async def recompute_session_score(db: AsyncSession, session_id: int) -> Optional[float]:
    """Recompute and persist Session.overall_score from all turns so far.

    Called incrementally per turn (NOT gated on /session/end) — a tab-close that
    never fires /end would otherwise leave the score NULL forever and bias the
    same-topic baseline toward only formally-ended sessions.
    """
    turn_data = await _load_turn_data(db, session_id)
    score = compute_overall_score(turn_data)
    sess = (
        await db.execute(select(DBSession).where(DBSession.id == session_id))
    ).scalar_one_or_none()
    if sess is not None:
        sess.overall_score = score
        await db.commit()
    return score


async def build_receipt(db: AsyncSession, session_id: int) -> Optional[Dict]:
    """Assemble the Growth Receipt: corrected-foregrounded replay + same-topic delta."""
    sess = (
        await db.execute(select(DBSession).where(DBSession.id == session_id))
    ).scalar_one_or_none()
    if sess is None:
        return None

    turn_data = await _load_turn_data(db, session_id)
    replay = [
        {
            "turn_id": t["id"],
            "user_corrected": t["corrected"],
            "user_raw": t["raw"],
            "ai_response": t["ai_response"],
            "error_count": t["error_count"],
        }
        for t in turn_data
    ]

    score = sess.overall_score

    # Same-topic priors, NULL scores excluded, chronological (id ~ creation order).
    priors = (
        await db.execute(
            select(DBSession.overall_score)
            .where(
                DBSession.topic == sess.topic,
                DBSession.id < sess.id,
                DBSession.overall_score.isnot(None),
            )
            .order_by(DBSession.id)
        )
    ).scalars().all()

    if len(priors) < 2:
        is_baseline = True
        trailing_avg = None
        delta = None
    else:
        is_baseline = False
        trailing_avg = round(sum(priors) / len(priors), 4)
        delta = round(score - trailing_avg, 4) if score is not None else None

    return {
        "session_id": sess.id,
        "topic": sess.topic,
        "turn_count": sess.turn_count or 0,
        "overall_score": score,
        "provisional": True,
        "is_baseline": is_baseline,
        "delta": delta,
        "trailing_avg": trailing_avg,
        "prior_session_count": len(priors),
        "replay": replay,
    }
