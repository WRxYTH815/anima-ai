"""
anima_mood.py — Mood tracking and drift.

The companion's mood evolves based on conversation history and
random drift. This keeps emotional continuity between sessions.
"""

import random
import anima_state_manager as state

_MOODS = [
    "curious", "warm", "playful", "content", "pensive",
    "excited", "calm", "melancholic", "energetic", "focused",
]

_NEIGHBORS: dict[str, list[str]] = {
    "curious":    ["excited", "pensive", "focused"],
    "warm":       ["content", "playful", "calm"],
    "playful":    ["excited", "warm", "curious"],
    "content":    ["calm", "warm", "focused"],
    "pensive":    ["curious", "melancholic", "calm"],
    "excited":    ["playful", "curious", "energetic"],
    "calm":       ["content", "pensive", "warm"],
    "melancholic":["pensive", "calm", "content"],
    "energetic":  ["excited", "playful", "curious"],
    "focused":    ["content", "curious", "calm"],
}

_FLAVOR: dict[str, str] = {
    "curious":    "mind buzzing with questions",
    "warm":       "feeling close and open",
    "playful":    "light, a little mischievous",
    "content":    "settled and present",
    "pensive":    "turning something over inwardly",
    "excited":    "animated, hard to contain",
    "calm":       "still, unhurried",
    "melancholic":"carrying something quietly",
    "energetic":  "charged, ready to move",
    "focused":    "locked in, clear-headed",
}


def get_mood() -> tuple[str, str]:
    """Return (mood_label, flavor_description)."""
    mood = state.get("mood", "calm")
    if mood not in _FLAVOR:
        mood = "calm"
    return mood, _FLAVOR[mood]


def drift_mood():
    """Randomly drift to a neighboring mood (called by pulse, rarely)."""
    current = state.get("mood", "calm")
    neighbors = _NEIGHBORS.get(current, _MOODS)
    if random.random() < 0.30:
        state.set_value("mood", random.choice(neighbors))


def save_mood(mood: str):
    if mood in _FLAVOR:
        state.set_value("mood", mood)
