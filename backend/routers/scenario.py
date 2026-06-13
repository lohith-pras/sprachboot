from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models.db import get_db, Scenario, get_or_create_preferences
from models.schemas import ScenarioCreate, ScenarioResponse
from services.scenario import generate_scenario, goals_to_json, goals_from_json
from services.profile_engine import estimate_level

router = APIRouter()


def _to_response(s: Scenario) -> ScenarioResponse:
    return ScenarioResponse(
        id=s.id,
        situation=s.situation,
        title=s.title,
        counterpart_role=s.counterpart_role,
        opening_line=s.opening_line,
        goals=goals_from_json(s.goals),
        topic=s.topic,
        status=s.status,
    )


@router.post("", response_model=ScenarioResponse)
async def create_scenario(req: ScenarioCreate, db: AsyncSession = Depends(get_db)):
    """Declare a real upcoming situation → generate a guard-railed role-play setup."""
    if not req.situation.strip():
        raise HTTPException(status_code=400, detail="situation is required")

    level = await estimate_level(db)
    prefs = await get_or_create_preferences(db)
    gen = await generate_scenario(req.situation.strip(), level=level, conv_model=prefs.conv_model)

    scenario = Scenario(
        situation=req.situation.strip(),
        title=gen["title"],
        counterpart_role=gen["counterpart_role"],
        opening_line=gen["opening_line"],
        goals=goals_to_json(gen["goals"]),
        topic="scenario",
        status="active",
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return _to_response(scenario)


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scenario).where(Scenario.status == "active").order_by(desc(Scenario.id))
    )
    return [_to_response(s) for s in result.scalars().all()]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    s = result.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _to_response(s)
