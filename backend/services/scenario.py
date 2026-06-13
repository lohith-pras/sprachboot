"""Scenario Studio: turn a real upcoming situation into a role-play setup.

The learner declares something like "doctor, knee pain, Tuesday"; the LLM expands it
into a guard-railed role-play: who the AI plays, its opening German line, and 3 concrete
goals the learner should achieve. The conversation engine then runs this speaking-first
with the difficulty controller, and the receipt is scoped to the scenario.
"""
import json
from typing import Dict, List
from services.openrouter_client import call_openrouter, LLAMA_MODEL

SCENARIO_PROMPT = """\
A German learner (level {level}) wants to rehearse a real upcoming situation:
"{situation}"

Design a focused role-play. Return ONLY valid JSON in this exact schema:
{{
  "title": "short label, max 6 words, in English",
  "counterpart_role": "who you will play, e.g. 'Hausärztin', 'Sachbearbeiter im Amt'",
  "opening_line": "your FIRST line to the learner, in natural German at level {level}, 1-2 sentences",
  "goals": ["3 concrete things the learner should manage to say/do, in English, short"]
}}

RULES:
- Return ONLY JSON. No preamble, no markdown.
- The situation is the learner's REAL life — be specific to it, do not invent unrelated details.
- opening_line MUST be German only and match level {level} (A1 = very simple).
- Exactly 3 goals.
"""


async def generate_scenario(
    situation: str, level: str = "A1", conv_model: str = LLAMA_MODEL
) -> Dict:
    """Generate a role-play setup from a free-text situation. Safe fallback on failure."""
    from services.openrouter_client import resolve_api_key

    fallback = {
        "title": situation[:60] or "Scenario",
        "counterpart_role": "Gesprächspartner",
        "opening_line": "Hallo! Wie kann ich Ihnen helfen?",
        "goals": ["Explain why you are here", "Answer one follow-up question", "Say thank you and goodbye"],
    }
    if not resolve_api_key():
        return fallback

    prompt = SCENARIO_PROMPT.format(situation=situation, level=level)
    try:
        raw = await call_openrouter(
            conv_model,
            [{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        data = json.loads(raw) if raw else fallback
    except Exception as e:
        print(f"[scenario] generation failed: {e}")
        return fallback

    # Normalize / guard shape.
    goals = data.get("goals") or fallback["goals"]
    if not isinstance(goals, list):
        goals = fallback["goals"]
    return {
        "title": (data.get("title") or fallback["title"])[:120],
        "counterpart_role": (data.get("counterpart_role") or fallback["counterpart_role"])[:80],
        "opening_line": data.get("opening_line") or fallback["opening_line"],
        "goals": goals[:3],
    }


def goals_to_json(goals: List[str]) -> str:
    return json.dumps(goals, ensure_ascii=False)


def goals_from_json(blob: str | None) -> List[str]:
    if not blob:
        return []
    try:
        v = json.loads(blob)
        return v if isinstance(v, list) else []
    except Exception:
        return []
