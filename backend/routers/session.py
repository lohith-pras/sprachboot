from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.db import get_db, Session as DBSession, Turn, get_or_create_preferences
from models.schemas import TurnRequest, TurnResponse, SessionEndRequest, SessionEndResponse
from services.conversation import build_conversation_response
from services.error_analysis import analyze_errors_background
from services.memory import get_weak_patterns, get_low_confidence_words
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Auto-create session if not provided
    if req.session_id is None:
        new_session = DBSession(mode=req.mode, topic=req.topic)
        db.add(new_session)
        await db.flush()
        session_id = new_session.id
    else:
        session_id = req.session_id
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found")

    # Get memory context
    weak_patterns = await get_weak_patterns(db, limit=5)
    low_conf_words = await get_low_confidence_words(db, limit=10)
    chroma_context = get_relevant_context(req.user_input, limit=3)

    prefs = await get_or_create_preferences(db)

    # Call AI for response
    ai_response, english_switch = await build_conversation_response(
        user_input=req.user_input,
        mode=req.mode,
        topic=req.topic,
        weak_patterns=weak_patterns,
        low_conf_words=low_conf_words,
        chroma_context=chroma_context,
        conv_model=prefs.conv_model,
        fallback_model=prefs.analysis_model,
    )

    # Store the turn
    turn = Turn(
        session_id=session_id,
        user_raw=req.user_input,
        ai_response=ai_response,
        had_english_switch=english_switch,
    )
    db.add(turn)
    await db.flush()
    turn_id = turn.id

    # Update session turn count
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    sess = result.scalar_one()
    sess.turn_count = (sess.turn_count or 0) + 1

    await db.commit()
    
    # Save to AI Memory (ChromaDB)
    add_turn_to_memory(session_id, req.user_input, ai_response)

    # Trigger background error analysis (non-blocking)
    background_tasks.add_task(
        analyze_errors_background,
        turn_id=turn_id,
        user_raw=req.user_input,
        ai_response=ai_response,
    )

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
    return SessionEndResponse(
        session_id=sess.id,
        turn_count=sess.turn_count,
        duration_s=sess.duration_s,
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
