from fastapi import APIRouter, HTTPException

from models.schemas import (
    TranslateWordRequest, TranslateSentenceRequest, TranslateResponse,
)
from services import translation

router = APIRouter()


@router.post("/word", response_model=TranslateResponse)
async def translate_word(body: TranslateWordRequest):
    result = await translation.translate_word(body.word)
    if result is None:
        raise HTTPException(status_code=503, detail="Translation unavailable")
    return TranslateResponse(translation=result)


@router.post("/sentence", response_model=TranslateResponse)
async def translate_sentence(body: TranslateSentenceRequest):
    result = await translation.translate_sentence(body.text)
    if result is None:
        raise HTTPException(status_code=503, detail="Translation unavailable")
    return TranslateResponse(translation=result)
