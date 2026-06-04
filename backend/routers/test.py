from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import get_db, TestResult
from models.schemas import TestGenerateResponse, TestSubmitRequest, TestSubmitResponse
from services.test_engine import generate_weekly_test, evaluate_test
from services.profile_engine import estimate_level
import json

router = APIRouter()

@router.get("/weekly", response_model=TestGenerateResponse)
async def get_weekly_test(level: str = "A1"):
    test_data = await generate_weekly_test(level)
    return TestGenerateResponse(**test_data)

@router.post("/weekly/submit", response_model=TestSubmitResponse)
async def submit_weekly_test(req: TestSubmitRequest, db: AsyncSession = Depends(get_db)):
    result = await evaluate_test(req.level, req.answers)
    
    # Store in DB
    tr = TestResult(
        test_type="weekly",
        cefr_level=req.level,
        score=result["score"],
        sections=json.dumps(result["details"])
    )
    db.add(tr)
    await db.commit()

    # Calculate actual dynamic level after saving test
    real_level = await estimate_level(db)
    result["cefr_level"] = real_level

    return TestSubmitResponse(**result)
