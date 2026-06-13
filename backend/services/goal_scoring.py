"""Scenario goal scoring — did the learner actually accomplish what they came to do?

Closes Open Question #1's "% of scenario goals hit" metric. After a scenario session,
an LLM judges the transcript against the declared goals and returns a hit/miss per goal.
This is the honest, scenario-scoped evidence the receipt foregrounds.
"""
import json
from typing import Dict, List

GOAL_PROMPT = """\
A German learner rehearsed this real-life situation: "{situation}"
They were trying to accomplish these goals:
{goal_lines}

Here is the conversation transcript (LEARNER = the learner, PARTNER = the role-play partner):
{transcript}

For EACH goal, decide whether the LEARNER actually accomplished it during this conversation.
Judge only the learner's own utterances — not the partner's. Be fair but honest: partial or
attempted does NOT count as hit.

Return ONLY valid JSON in this exact schema:
{{"results": [{{"goal": "the goal text", "hit": true_or_false}}]}}
No preamble, no markdown.
"""


def score_goals_fallback(goals: List[str]) -> List[Dict]:
    return [{"goal": g, "hit": False} for g in goals]


async def score_goals(
    situation: str, goals: List[str], transcript: str, analysis_model: str
) -> List[Dict]:
    """Return [{"goal": str, "hit": bool}, ...]. Falls back to all-miss on any failure."""
    from services.openrouter_client import call_openrouter, resolve_api_key

    if not goals:
        return []
    if not resolve_api_key() or not transcript.strip():
        return score_goals_fallback(goals)

    goal_lines = "\n".join(f"- {g}" for g in goals)
    prompt = GOAL_PROMPT.format(
        situation=situation, goal_lines=goal_lines, transcript=transcript
    )
    try:
        raw = await call_openrouter(
            analysis_model,
            [{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(raw) if raw else {}
        results = data.get("results")
        if not isinstance(results, list):
            return score_goals_fallback(goals)
    except Exception as e:
        print(f"[goal_scoring] failed: {e}")
        return score_goals_fallback(goals)

    # Re-align to the declared goals by order, coercing hit → bool.
    out: List[Dict] = []
    for i, g in enumerate(goals):
        hit = bool(results[i].get("hit")) if i < len(results) and isinstance(results[i], dict) else False
        out.append({"goal": g, "hit": hit})
    return out


def goals_hit_to_json(results: List[Dict]) -> str:
    return json.dumps(results, ensure_ascii=False)


def goals_hit_from_json(blob: str | None) -> List[Dict]:
    if not blob:
        return []
    try:
        v = json.loads(blob)
        return v if isinstance(v, list) else []
    except Exception:
        return []
