"""Simplified SM-2 spaced repetition algorithm (CLAUDE.md §10)."""
from datetime import datetime, timedelta


def update_interval(current_interval: int, was_correct: bool) -> int:
    """
    Simplified SM-2:
    - Correct: interval *= 2 (max 30 days)
    - Incorrect: reset to 1 day
    Returns the new interval in days.
    """
    if was_correct:
        return min(current_interval * 2, 30)
    else:
        return 1
