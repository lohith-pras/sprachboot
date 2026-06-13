from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.db import get_db, Session as DBSession, Turn, Scenario, get_or_create_preferences, AsyncSessionLocal
from models.schemas import (
    TurnRequest, TurnResponse, SessionEndRequest, SessionEndResponse,
    ReceiptResponse, ReceiptTurn, GoalResult,
)
from services.conversation import build_conversation_response
from services.error_analysis import analyze_errors, persist_analysis
from services.memory import get_weak_patterns, get_low_confidence_words, get_session_history
from services.profile_engine import estimate_level
from services.receipt import recompute_session_score, build_receipt
from services.difficulty import compute_difficulty
from services.scenario import goals_from_json
from services.goal_scoring import score_goals, goals_hit_to_json
from datetime import datetime
from services.chroma_service import get_relevant_context, add_turn_to_memory
import tempfile
import os
from typing import Optional

router = APIRouter()

_whisper_model: Optional[object] = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model


@router.post("/turn", response_model=TurnResponse)
async def session_turn(
    req: TurnRequest,
    db: AsyncSession = Depends(get_db),
):
    # Auto-create session if not provided. A scenario session is topic-tagged
    # "scenario:<id>" so PR1's same-topic receipt delta auto-scopes per scenario.
    if req.session_id is None:
        topic = f"scenario:{req.scenario_id}" if req.scenario_id else req.topic
        new_session = DBSession(mode=req.mode, topic=topic, scenario_id=req.scenario_id)
        db.add(new_session)
        await db.flush()
        session_id = new_session.id
    else:
        session_id = req.session_id
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found")

    # Step 1: Analyze current input synchronously — closes the learning loop
    weak_patterns_before = await get_weak_patterns(db, limit=5)
    previously_weak_keys = [p["pattern_key"] for p in weak_patterns_before]
    analysis = await analyze_errors(req.user_input)

    # Step 2: Store turn (need turn_id before persist_analysis writes errors)
    turn = Turn(
        session_id=session_id,
        user_raw=req.user_input,
        user_corrected=analysis.get("corrected"),
        error_count=len(analysis.get("errors", [])),
    )
    db.add(turn)
    await db.flush()
    turn_id = turn.id

    result2 = await db.execute(select(DBSession).where(DBSession.id == session_id))
    sess = result2.scalar_one()
    sess.turn_count = (sess.turn_count or 0) + 1
    await db.commit()

    # Step 3: Persist errors + success signals synchronously so state is fresh
    await persist_analysis(turn_id, analysis, previously_weak_keys)

    # Step 4: Re-read state — now reflects this turn's errors and successes
    async with AsyncSessionLocal() as fresh_db:
        weak_patterns = await get_weak_patterns(fresh_db, limit=5)
        low_conf_words = await get_low_confidence_words(fresh_db, limit=10)
        current_level = await estimate_level(fresh_db)
        history = await get_session_history(fresh_db, session_id, before_turn_id=turn_id)

        # Closed-loop difficulty: react to the most recent turns (incl. this one).
        recent = (
            await fresh_db.execute(
                select(Turn).where(Turn.session_id == session_id)
                .order_by(Turn.id.desc()).limit(3)
            )
        ).scalars().all()
        recent_signals = [
            {"error_count": t.error_count or 0, "word_count": len((t.user_raw or "").split())}
            for t in reversed(recent)
        ]
        difficulty = compute_difficulty(recent_signals)

        # Load scenario role-play setup if this is a scenario session.
        sess_row = (
            await fresh_db.execute(select(DBSession).where(DBSession.id == session_id))
        ).scalar_one_or_none()
        scenario_obj = None
        sc_id = getattr(sess_row, "scenario_id", None) or req.scenario_id
        if sc_id:
            s = (
                await fresh_db.execute(select(Scenario).where(Scenario.id == sc_id))
            ).scalar_one_or_none()
            if s is not None:
                scenario_obj = {
                    "counterpart_role": s.counterpart_role,
                    "situation": s.situation,
                    "goals": goals_from_json(s.goals),
                }

    chroma_context = get_relevant_context(req.user_input, limit=3)
    prefs = await get_or_create_preferences(db)

    # Step 5: Build conversation prompt with fully up-to-date state + in-session memory
    ai_response, english_switch = await build_conversation_response(
        user_input=req.user_input,
        mode=req.mode,
        topic=req.topic,
        weak_patterns=weak_patterns,
        low_conf_words=low_conf_words,
        current_level=current_level,
        chroma_context=chroma_context,
        history=history,
        scenario=scenario_obj,
        difficulty_directive=difficulty["directive"],
        conv_model=prefs.conv_model,
        fallback_model=prefs.analysis_model,
    )

    # Step 6: Update turn with AI response
    async with AsyncSessionLocal() as upd_db:
        upd_result = await upd_db.execute(select(Turn).where(Turn.id == turn_id))
        upd_turn = upd_result.scalar_one()
        upd_turn.ai_response = ai_response
        upd_turn.had_english_switch = english_switch
        await upd_db.commit()

    # Save to ChromaDB
    add_turn_to_memory(session_id, req.user_input, ai_response)

    # Step 7: Recompute overall_score incrementally — NOT gated on /session/end.
    # A tab-close means /end may never fire; a NULL score would skew the baseline.
    async with AsyncSessionLocal() as score_db:
        await recompute_session_score(score_db, session_id)

    return TurnResponse(
        turn_id=turn_id,
        session_id=session_id,
        ai_response=ai_response,
        english_switch=english_switch,
        errors=[],          # filled by background task; poll GET /session/turn/{id}
        corrected_input=None,
    )


@router.post("/end", response_model=SessionEndResponse)
async def session_end(
    req: SessionEndRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DBSession).where(DBSession.id == req.session_id))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    sess.duration_s = req.duration_s
    await db.commit()

    # Scenario session: score goals against the transcript + arm the transfer loop.
    if sess.scenario_id:
        await _score_scenario_and_arm_transfer(db, sess)

    return SessionEndResponse(
        session_id=sess.id,
        turn_count=sess.turn_count,
        duration_s=sess.duration_s,
    )


async def _score_scenario_and_arm_transfer(db: AsyncSession, sess: DBSession):
    scenario = (
        await db.execute(select(Scenario).where(Scenario.id == sess.scenario_id))
    ).scalar_one_or_none()
    if scenario is None:
        return
    goals = goals_from_json(scenario.goals)
    turns = (
        await db.execute(
            select(Turn).where(Turn.session_id == sess.id).order_by(Turn.id)
        )
    ).scalars().all()
    transcript = "\n".join(
        f"LEARNER: {t.user_corrected or t.user_raw}\nPARTNER: {t.ai_response or ''}"
        for t in turns
    )
    prefs = await get_or_create_preferences(db)
    results = await score_goals(
        scenario.situation, goals, transcript, prefs.analysis_model
    )
    sess.goals_hit = goals_hit_to_json(results)
    scenario.transfer_status = "pending"
    scenario.last_practiced_at = datetime.now()
    await db.commit()


@router.get("/{session_id}/receipt", response_model=ReceiptResponse)
async def session_receipt(session_id: int, db: AsyncSession = Depends(get_db)):
    """Growth Receipt: corrected-foregrounded replay + same-topic delta."""
    receipt = await build_receipt(db, session_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return ReceiptResponse(
        session_id=receipt["session_id"],
        topic=receipt["topic"],
        turn_count=receipt["turn_count"],
        overall_score=receipt["overall_score"],
        provisional=receipt["provisional"],
        is_baseline=receipt["is_baseline"],
        delta=receipt["delta"],
        trailing_avg=receipt["trailing_avg"],
        prior_session_count=receipt["prior_session_count"],
        replay=[ReceiptTurn(**t) for t in receipt["replay"]],
        scenario_title=receipt["scenario_title"],
        counterpart_role=receipt["counterpart_role"],
        goals=[GoalResult(**g) for g in receipt["goals"]],
    )


@router.get("/turn/{turn_id}")
async def get_turn_errors(turn_id: int, db: AsyncSession = Depends(get_db)):
    """Poll this after POST /session/turn to get background error analysis results."""
    result = await db.execute(select(Turn).where(Turn.id == turn_id))
    turn = result.scalar_one_or_none()
    if not turn:
        raise HTTPException(status_code=404, detail="Turn not found")

    from models.db import Error
    from models.schemas import ErrorItem
    err_result = await db.execute(select(Error).where(Error.turn_id == turn_id))
    errors = err_result.scalars().all()

    return {
        "turn_id": turn_id,
        "corrected_input": turn.user_corrected,
        "error_count": turn.error_count,
        "errors": [
            ErrorItem(
                error_type=e.error_type,
                pattern_key=e.pattern_key,
                severity=e.severity,
                user_fragment=e.user_fragment,
                correct_form=e.correct_form,
                rule_shown=e.rule_shown,
            )
            for e in errors
        ],
    }


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribes an uploaded audio file to text using faster-whisper."""
    model = _get_whisper_model()
    
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
        
    try:
        # initial_prompt provides context and hints common vocabulary to Whisper
        prompt = "Hallo! Lass uns auf Deutsch unterhalten. Ja sicher, was machst du heute?"
        segments, info = model.transcribe(tmp_path, language="de", initial_prompt=prompt)
        text = " ".join([segment.text for segment in segments])
        return {"text": text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
