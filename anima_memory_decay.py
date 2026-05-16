"""
Memory decay — emotional memories fade at different rates.
High-valence emotions (joy, fear, love) last longer; neutral fades fast.
"""

import datetime

_HALF_LIVES: dict[str, int] = {
    "joy":       90,
    "love":      120,
    "fear":      60,
    "sadness":   45,
    "anger":     30,
    "surprise":  20,
    "neutral":   14,
}
_DEFAULT_HALF_LIFE = 30  # days


def get_half_life(emotion: str) -> int:
    return _HALF_LIVES.get(emotion.lower(), _DEFAULT_HALF_LIFE)


def decay_score(similarity: float, timestamp_iso: str, half_life_days: int) -> float:
    """Returns similarity weighted by how fresh the memory is."""
    try:
        ts   = datetime.datetime.fromisoformat(timestamp_iso)
        age  = (datetime.datetime.now() - ts).total_seconds() / 86400
        factor = 0.5 ** (age / max(half_life_days, 1))
        return similarity * factor
    except Exception:
        return similarity * 0.5
