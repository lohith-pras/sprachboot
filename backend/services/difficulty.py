"""Closed-loop difficulty controller — the Regelkreis.

Sensors (error rate + sentence length over recent turns) are compared to a flow setpoint
(challenge ≈ skill + small ε). The actuator is a directive injected into the next turn's
system prompt. Per the design: start prompt-level, measure drift, escalate only if needed.

Three bands:
- ease    : recent errors high → the learner is past the flow channel into frustration.
- stretch : recent errors near zero AND sentences short/safe → too easy, nudge harder.
- hold    : in the flow channel → keep difficulty steady.
"""
from typing import Dict, List

EASE_ERROR_RATE = 1.5    # avg errors/turn above this → make it easier
STRETCH_ERROR_RATE = 0.5  # avg errors/turn below this (and short) → push harder
SAFE_LEN = 6              # avg words/turn at/below this counts as "playing it safe"
RECENT_WINDOW = 3        # how many recent turns the controller reacts to

_DIRECTIVES = {
    "ease": (
        "DIFFICULTY: The learner is struggling. Make THIS reply easier — one short simple "
        "sentence, only common A1/A2 words, ask a small concrete question they can answer."
    ),
    "hold": (
        "DIFFICULTY: The learner is in their flow channel. Keep the current difficulty — "
        "natural, 1-2 sentences, no sudden jump in complexity."
    ),
    "stretch": (
        "DIFFICULTY: The learner is finding this easy and keeping it safe. Gently raise the "
        "challenge — use a slightly longer sentence or a subordinate clause (weil/dass/wenn) "
        "and one richer word, while staying near their level."
    ),
}


def compute_difficulty(recent_turns: List[Dict]) -> Dict:
    """recent_turns: newest-last list of {"error_count": int, "word_count": int}.

    Returns {"band": str, "directive": str}. Empty history → 'hold'.
    """
    window = [t for t in recent_turns if t is not None][-RECENT_WINDOW:]
    if not window:
        return {"band": "hold", "directive": _DIRECTIVES["hold"]}

    n = len(window)
    error_rate = sum(t.get("error_count", 0) for t in window) / n
    avg_len = sum(t.get("word_count", 0) for t in window) / n

    if error_rate > EASE_ERROR_RATE:
        band = "ease"
    elif error_rate < STRETCH_ERROR_RATE and avg_len <= SAFE_LEN:
        band = "stretch"
    else:
        band = "hold"
    return {"band": band, "directive": _DIRECTIVES[band]}
