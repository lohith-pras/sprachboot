import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import get_db, get_or_create_preferences
from models.schemas import (
    PreferencesResponse, PreferencesUpdate, ApiKeySet, ApiKeyStatus,
    ApiKeyTestRequest, ApiKeyTestResult, ModelOption, ModelsResponse,
)
from services import keychain

router = APIRouter()

_models_cache: dict = {"ts": 0.0, "data": None}
_CACHE_TTL = 3600


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    p = await get_or_create_preferences(db)
    return PreferencesResponse(
        user_name=p.user_name,
        conv_model=p.conv_model,
        analysis_model=p.analysis_model,
        onboarding_complete=p.onboarding_complete,
    )


@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(body: PreferencesUpdate, db: AsyncSession = Depends(get_db)):
    p = await get_or_create_preferences(db)
    for field in ("user_name", "conv_model", "analysis_model", "onboarding_complete"):
        val = getattr(body, field)
        if val is not None:
            setattr(p, field, val)
    await db.commit()
    await db.refresh(p)
    return PreferencesResponse(
        user_name=p.user_name,
        conv_model=p.conv_model,
        analysis_model=p.analysis_model,
        onboarding_complete=p.onboarding_complete,
    )


@router.post("/apikey")
async def set_apikey(body: ApiKeySet):
    try:
        keychain.set_key(body.service, body.key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/apikey/status", response_model=ApiKeyStatus)
async def apikey_status():
    return ApiKeyStatus(**keychain.key_status())


@router.post("/apikey/test", response_model=ApiKeyTestResult)
async def apikey_test(body: ApiKeyTestRequest):
    key = keychain.get_key(body.service)
    if not key:
        return ApiKeyTestResult(ok=False, detail="No key stored")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if body.service == "openrouter":
                r = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
            elif body.service == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
            else:  # deepl
                r = await client.get(
                    "https://api-free.deepl.com/v2/usage",
                    headers={"Authorization": f"DeepL-Auth-Key {key}"},
                )
        return ApiKeyTestResult(ok=r.status_code == 200,
                                detail=None if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as e:
        return ApiKeyTestResult(ok=False, detail=str(e))


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    now = time.time()
    if _models_cache["data"] and now - _models_cache["ts"] < _CACHE_TTL:
        return ModelsResponse(models=_models_cache["data"])

    key = keychain.get_key("openrouter")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
            r.raise_for_status()
            raw = r.json().get("data", [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch models: {e}")

    models = [
        ModelOption(id=m["id"], name=m.get("name", m["id"]))
        for m in raw
        if m.get("id")
    ]
    _models_cache["data"] = models
    _models_cache["ts"] = now
    return ModelsResponse(models=models)
