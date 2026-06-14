import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_db, get_or_create_preferences
from services.memory import get_low_confidence_words
from services.openrouter_client import call_openrouter

router = APIRouter()

# Hardcoded for the Phase 4 MVP — in prod, generate these from the learner's
# weak words rather than a fixed list.
SCENARIOS = [
    {
        "id": "s1",
        "prompt": "Du bist im Restaurant und möchtest bezahlen. Was sagst du?",
        "target_word": "bezahlen",
    },
    {
        "id": "s2",
        "prompt": "Ein Freund fragt dich, was du am Wochenende machst. Du gehst ins Kino. Antworte ihm.",
        "target_word": "Kino",
    },
    {
        "id": "s3",
        "prompt": "Du bist im Supermarkt und kannst die Milch nicht finden. Frag den Verkäufer.",
        "target_word": "Milch",
    },
]


@router.get("/deck")
async def get_review_deck(db: AsyncSession = Depends(get_db)):
    """Return practice scenarios plus the learner's current low-confidence focus words."""
    low_conf_words = await get_low_confidence_words(db, limit=3)
    return {"scenarios": SCENARIOS, "focus_words": low_conf_words}


class ReviewCheckRequest(BaseModel):
    scenario_prompt: str
    user_response: str


REVIEW_CHECK_PROMPT = """\
The user was given this scenario in German: "{scenario_prompt}"
The user responded: "{user_response}"

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
IMPORTANT: Completely ignore noun capitalization and minor spelling mistakes. Do NOT flag them.
"""


@router.post("/check")
async def check_review_response(
    req: ReviewCheckRequest, db: AsyncSession = Depends(get_db)
):
    """Score a single review-scenario response via the shared analysis model.

    Routed through call_openrouter so it uses the same key resolution (onboarding
    key, then env) and error handling as the rest of the app. This previously
    reimplemented the HTTP call inline and only ever saw the env key.
    """
    prefs = await get_or_create_preferences(db)
    prompt = REVIEW_CHECK_PROMPT.format(
        scenario_prompt=req.scenario_prompt, user_response=req.user_response
    )
    try:
        raw = await call_openrouter(
            prefs.analysis_model,
            [{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(raw)
    except Exception as e:
        print(f"[review] check failed: {e}")
        return {"corrected": req.user_response, "errors": []}
