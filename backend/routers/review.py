from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import get_db
from models.schemas import TurnResponse
from services.memory import get_weak_patterns, get_low_confidence_words
from services.error_analysis import analyze_errors_background

router = APIRouter()

# Hardcoded for Phase 4 MVP - in prod, use LLM to generate these dynamically based on weak words
SCENARIOS = [
    {
        "id": "s1",
        "prompt": "Du bist im Restaurant und möchtest bezahlen. Was sagst du?",
        "target_word": "bezahlen"
    },
    {
        "id": "s2",
        "prompt": "Ein Freund fragt dich, was du am Wochenende machst. Du gehst ins Kino. Antworte ihm.",
        "target_word": "Kino"
    },
    {
        "id": "s3",
        "prompt": "Du bist im Supermarkt und kannst die Milch nicht finden. Frag den Verkäufer.",
        "target_word": "Milch"
    }
]

@router.get("/deck")
async def get_review_deck(db: AsyncSession = Depends(get_db)):
    # In a real implementation, we would use weak_patterns and low_conf_words to pick/generate scenarios
    weak_patterns = await get_weak_patterns(db, limit=3)
    low_conf_words = await get_low_confidence_words(db, limit=3)
    
    return {
        "scenarios": SCENARIOS,
        "focus_words": low_conf_words
    }

from pydantic import BaseModel
class ReviewCheckRequest(BaseModel):
    scenario_prompt: str
    user_response: str

@router.post("/check")
async def check_review_response(req: ReviewCheckRequest):
    # For Phase 4 MVP, we will just use the standard deepseek error analysis!
    # We can run it synchronously here since it's a dedicated review check
    from dotenv import load_dotenv
    import os
    import httpx
    
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    
    # Prompt DeepSeek to evaluate if the response fits the scenario
    prompt = f"""
    The user was given this scenario in German: "{req.scenario_prompt}"
    The user responded: "{req.user_response}"
    
    Analyze the user's response. Return ONLY valid JSON in this exact schema:
    {{
      "corrected": "string - a natural, correct way to say this",
      "errors": [
        {{
          "error_type": "vocab|grammar",
          "pattern_key": "key",
          "severity": "high|medium|low",
          "user_fragment": "mistake",
          "correct_form": "fix",
          "rule": "explanation"
        }}
      ]
    }}
    If the response is completely inappropriate for the scenario, flag it as a 'vocab' error.
    IMPORTANT: Completely ignore noun capitalization and minor spelling mistakes. Do NOT flag them as errors.
    """
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek/deepseek-v4-flash",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }
        )
        data = res.json()
        raw_json = data["choices"][0]["message"].get("content", "{}")
        import json
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = {"corrected": req.user_response, "errors": []}
        
    return parsed
