"""Builds the Llama prompt and calls OpenRouter. Falls back to DeepSeek on rate-limit."""
import os
import httpx
from typing import List, Dict, Tuple
from services.openrouter_client import call_openrouter, LLAMA_MODEL, DEEPSEEK_MODEL

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
    conv_model: str = LLAMA_MODEL,
    fallback_model: str = DEEPSEEK_MODEL,
) -> Tuple[str, bool]:
    """Returns (ai_response_text, english_switch_flag). Falls back on 429."""
    from services.openrouter_client import resolve_api_key
    if not resolve_api_key():
        return (
            "Entschuldigung, der API-Schlüssel fehlt. Bitte konfiguriere OPENROUTER_API_KEY.",
            False,
        )

    weak_str = ", ".join(p["pattern_key"] for p in weak_patterns) or "none yet"
    low_conf_str = ", ".join(low_conf_words) or "none yet"

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        current_level=current_level,
        weak_patterns=weak_str,
        low_conf_words=low_conf_str,
        topic=topic,
        chroma_context=chroma_context or "(no past context yet)",
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        text = await call_openrouter(conv_model, messages, max_tokens=200, temperature=0.7)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            text = await call_openrouter(fallback_model, messages, max_tokens=200, temperature=0.7)
        else:
            raise

    return text, _detect_english_switch(text)
