"""Builds the conversation prompt and calls OpenRouter, with a fallback model on failure."""
import httpx
from typing import List, Dict, Tuple
from services.openrouter_client import call_openrouter, CONV_MODEL, DEEPSEEK_MODEL

SYSTEM_PROMPT_TEMPLATE = """\
You are a friendly German conversation partner helping a learner reach B1 conversational fluency.

LEARNER PROFILE (from memory):
- Current level: {current_level}
- Recurring weak patterns: {weak_patterns}
- Low-confidence words to weave in naturally: {low_conf_words}

CONVERSATION RULES:
1. PRIMARY LANGUAGE: Speak German at {current_level} difficulty. Do not use English unless the user explicitly asks for it or you are making a quick grammar correction.
2. Keep responses SHORT — 1–2 sentences max. You are a conversation partner, not a teacher.
3. If the learner makes a SEVERE error (V2 violation, wrong gender + case together), briefly switch to English to explain ONE thing, then immediately return to German. Format: "[EN: Quick explanation] Auf Deutsch: [your response]"
4. Do NOT correct every small mistake — only high-severity or recurring patterns.
5. Focus the conversation strictly on this topic: {topic}
6. NEVER explain or correct noun capitalization. Ignore missing capitalization entirely.
7. Weave in topics the user has previously mentioned when natural.
8. TRANSLATIONS & EXPLANATIONS: If the user explicitly asks for a translation or explanation in English (e.g. "what does X mean?", "in english"), YOU MUST answer them in English to explain. Do not refuse. After explaining, gently prompt them to continue in German.
9. Never lecture. Never give grammar tables. You are having a conversation.

PAST CONTEXT (last similar sessions):
{chroma_context}

{difficulty_directive}
"""

SCENARIO_PROMPT_TEMPLATE = """\
You are role-playing a real-life German situation so a learner can rehearse it before doing it for real.

YOUR ROLE: You are the {counterpart_role}. Stay fully in character — you are NOT a teacher.
THE SITUATION: {situation}
LEARNER GOALS (do NOT reveal or list these; just play the scene so they naturally arise): {goals}

LEARNER PROFILE:
- Current level: {current_level}
- Recurring weak patterns: {weak_patterns}
- Low-confidence words to weave in naturally: {low_conf_words}

CONVERSATION RULES:
1. Speak German at {current_level} difficulty, in character as the {counterpart_role}.
2. Keep replies SHORT — 1–2 sentences — and keep the scene moving with natural questions.
3. If the learner makes a SEVERE error (V2 violation, wrong gender + case together), briefly switch to English for ONE correction, then return to German IN CHARACTER. Format: "[EN: Quick explanation] Auf Deutsch: [your line]"
4. Do NOT correct small mistakes. Do NOT break character to lecture.
5. NEVER explain or correct noun capitalization. Ignore it entirely.
6. If the learner explicitly asks for a translation/explanation in English, answer in English, then return to the scene in German.
7. When the learner has clearly handled the situation, wrap the scene up naturally.

{difficulty_directive}
"""


def _detect_english_switch(ai_response: str | None) -> bool:
    return bool(ai_response) and "[EN:" in ai_response


async def build_conversation_response(
    user_input: str,
    mode: str,
    topic: str,
    weak_patterns: List[Dict],
    low_conf_words: List[str],
    current_level: str = "A1",
    chroma_context: str = "",
    history: List[Dict] | None = None,
    scenario: Dict | None = None,
    difficulty_directive: str = "",
    conv_model: str = CONV_MODEL,
    fallback_model: str = DEEPSEEK_MODEL,
) -> Tuple[str, bool]:
    """Returns (ai_response_text, english_switch_flag). Falls back to fallback_model
    on any model failure (rate limit, empty content, bad id).

    `history` is the in-session [{"role": "user"|"assistant", "content": str}, ...]
    of prior turns so the model has conversational memory, not a one-shot reply.
    `scenario`, when present, switches to a role-play system prompt.
    `difficulty_directive` is the closed-loop controller's actuation for this turn.
    """
    from services.openrouter_client import resolve_api_key
    if not resolve_api_key():
        return (
            "Entschuldigung, der API-Schlüssel fehlt. Bitte konfiguriere OPENROUTER_API_KEY.",
            False,
        )

    weak_str = ", ".join(p["pattern_key"] for p in weak_patterns) or "none yet"
    low_conf_str = ", ".join(low_conf_words) or "none yet"

    if scenario:
        from services.scenario import goals_from_json
        goals = scenario.get("goals")
        if isinstance(goals, str):
            goals = goals_from_json(goals)
        system_prompt = SCENARIO_PROMPT_TEMPLATE.format(
            counterpart_role=scenario.get("counterpart_role") or "Gesprächspartner",
            situation=scenario.get("situation") or topic,
            goals="; ".join(goals or []) or "(none specified)",
            current_level=current_level,
            weak_patterns=weak_str,
            low_conf_words=low_conf_str,
            difficulty_directive=difficulty_directive,
        )
    else:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            current_level=current_level,
            weak_patterns=weak_str,
            low_conf_words=low_conf_str,
            topic=topic,
            chroma_context=chroma_context or "(no past context yet)",
            difficulty_directive=difficulty_directive,
        )

    messages = [
        {"role": "system", "content": system_prompt},
        *(history or []),
        {"role": "user", "content": user_input},
    ]

    try:
        text = await call_openrouter(conv_model, messages, max_tokens=200, temperature=0.7)
    except httpx.HTTPStatusError:
        # Rate limit, empty content, bad model id, etc. → try the fallback model
        # before failing the whole turn.
        text = await call_openrouter(fallback_model, messages, max_tokens=200, temperature=0.7)

    return text, _detect_english_switch(text)
