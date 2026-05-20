"""
anima_emotion.py — Plutchik's Wheel emotion engine with exponential decay.

Inspired by Synthetic Heart's emotion_manager.
Emotions decay naturally over time: I(t) = I₀ · e^(-t/τ)
Opposite emotions suppress each other on the Plutchik wheel.
No model required — keyword heuristics for detection.
"""

import math
import time
import threading

# ── Plutchik's 8 basic emotions + common dyads ────────────────────────────────

EMOTIONS: set[str] = {
    # Basic 8
    "joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation",
    # Primary dyads
    "love", "submission", "awe", "disapproval", "remorse", "contempt", "aggression", "optimism",
    # Neutral
    "neutral",
}

# Opposites suppress each other when a new emotion fires
_OPPOSITES: dict[str, str] = {
    "joy":          "sadness",
    "sadness":      "joy",
    "trust":        "disgust",
    "disgust":      "trust",
    "fear":         "anger",
    "anger":        "fear",
    "surprise":     "anticipation",
    "anticipation": "surprise",
    "love":         "remorse",
    "remorse":      "love",
    "optimism":     "disapproval",
    "disapproval":  "optimism",
    "aggression":   "submission",
    "submission":   "aggression",
}

_TAU = 300.0  # emotional half-life in seconds (5 min)

_state: dict[str, dict] = {}   # emotion -> {intensity: float, onset: float}
_lock  = threading.Lock()

# ── Detection keywords ────────────────────────────────────────────────────────

_KEYWORDS: dict[str, list[str]] = {
    "joy":          ["happy", "glad", "excited", "wonderful", "amazing", "great", "joy",
                     "delighted", "thrilled", "pleased", "fantastic", "love it"],
    "sadness":      ["sad", "sorry", "unfortunate", "miss", "lonely", "hurt", "grief",
                     "down", "depressed", "unhappy", "upset", "lost", "empty"],
    "anger":        ["angry", "frustrated", "annoyed", "furious", "mad", "irritated",
                     "hate", "rage", "outraged", "hostile"],
    "fear":         ["scared", "afraid", "nervous", "anxious", "worried", "terrified",
                     "dread", "panic", "uneasy", "apprehensive"],
    "surprise":     ["wow", "unexpected", "shocking", "surprised", "astonishing",
                     "sudden", "never expected", "unbelievable"],
    "disgust":      ["gross", "disgusting", "awful", "horrible", "repulsive",
                     "nasty", "revolting", "appalled"],
    "trust":        ["trust", "reliable", "honest", "confident", "safe",
                     "secure", "depend", "faithful"],
    "anticipation": ["excited", "looking forward", "can't wait", "hope", "soon",
                     "eager", "curious", "wondering"],
    "love":         ["love", "adore", "cherish", "dear", "care", "fond",
                     "affection", "precious", "treasure"],
    "optimism":     ["will be fine", "better", "positive", "hopeful", "bright",
                     "forward", "progress", "improve"],
}


# ── Core functions ────────────────────────────────────────────────────────────

def _decay(intensity: float, elapsed: float) -> float:
    return intensity * math.exp(-elapsed / _TAU)


def _prune(now: float):
    to_delete = [em for em, d in _state.items()
                 if _decay(d["intensity"], now - d["onset"]) < 0.01]
    for em in to_delete:
        del _state[em]
    for d in _state.values():
        d["intensity"] = _decay(d["intensity"], now - d["onset"])
        d["onset"]     = now


def feel(emotion: str, intensity: float = 0.7):
    """Register an emotional event. Suppresses opposite emotion proportionally."""
    if emotion not in EMOTIONS or emotion == "neutral":
        return
    intensity = max(0.0, min(1.0, intensity))
    now = time.time()
    with _lock:
        _prune(now)
        opp = _OPPOSITES.get(emotion)
        if opp and opp in _state:
            _state[opp]["intensity"] = max(0.0, _state[opp]["intensity"] - intensity * 0.4)
        existing = _state.get(emotion)
        if existing:
            new_intensity = min(1.0, existing["intensity"] + intensity)
            _state[emotion] = {"intensity": new_intensity, "onset": now}
        else:
            _state[emotion] = {"intensity": intensity, "onset": now}


def dominant() -> str:
    now = time.time()
    with _lock:
        _prune(now)
        if not _state:
            return "neutral"
        return max(_state, key=lambda e: _state[e]["intensity"])


def get_all() -> dict[str, float]:
    now = time.time()
    with _lock:
        _prune(now)
        return {em: round(d["intensity"], 3) for em, d in _state.items()}


def detect_emotion(text: str) -> str:
    """
    Heuristic emotion detection from text.
    Fires feel() as a side-effect so detected emotions accumulate in state.
    """
    lower  = text.lower()
    scores: dict[str, int] = {}

    for emotion, words in _KEYWORDS.items():
        score = sum(1 for w in words if w in lower)
        if score:
            scores[emotion] = score

    if not scores:
        return dominant()

    detected  = max(scores, key=scores.__getitem__)
    intensity = min(0.4 * scores[detected], 0.8)
    feel(detected, intensity)
    return detected


def format_for_prompt() -> str:
    """Returns a compact emotion summary for system prompt injection."""
    emotions = get_all()
    if not emotions:
        return ""
    top   = sorted(emotions.items(), key=lambda x: -x[1])[:3]
    parts = ", ".join(f"{e} ({v:.0%})" for e, v in top)
    return f"[Emotional resonance: {parts}]"
