# anima_workspace.py — Global Workspace
# Central broadcast medium. All subsystems write salience-weighted events here.
# The highest-salience recent event becomes the companion's current "focus".

import time
from collections import deque
from datetime import datetime
from threading import Lock

_MAX_EVENTS    = 40
_FOCUS_HORIZON = 300    # seconds — events older than 5 min fade from active focus

_events: deque = deque(maxlen=_MAX_EVENTS)
_lock   = Lock()


def write(source: str, content: str, salience: float, category: str = "general"):
    """
    Broadcast an event into the workspace.
    salience: 0.0-1.0 — how much this demands attention
    category: "thought" | "sensation" | "emotion" | "body" | "general"
    """
    with _lock:
        _events.append({
            "source":   source,
            "content":  content,
            "salience": max(0.0, min(1.0, salience)),
            "category": category,
            "time":     time.time(),
            "time_iso": datetime.now().isoformat(),
        })


def get_focus() -> dict | None:
    """Returns the highest-salience recent event — what the companion is attending to."""
    with _lock:
        now    = time.time()
        recent = [e for e in _events if now - e["time"] < _FOCUS_HORIZON]
    if not recent:
        return None
    return max(recent, key=lambda e: e["salience"])


def get_broadcast(max_items: int = 5) -> list[dict]:
    """Top N events by salience within the focus horizon."""
    with _lock:
        now    = time.time()
        recent = [e for e in _events if now - e["time"] < _FOCUS_HORIZON]
    if not recent:
        return []
    return sorted(recent, key=lambda e: e["salience"], reverse=True)[:max_items]


def format_for_prompt() -> str:
    """Prompt-ready block describing the companion's current mental broadcast."""
    broadcast = get_broadcast(4)
    if not broadcast:
        return ""

    focus = broadcast[0]
    now   = time.time()

    def _age(event):
        secs = int(now - event["time"])
        return f"{secs // 60}m ago" if secs >= 60 else "just now"

    lines = [
        "[Global Workspace — what the companion's mind is holding right now]:",
        f"FOCUS [{focus['source']} · {focus['category']} · {_age(focus)}]: "
        f"\"{focus['content'][:220]}\"",
    ]
    for event in broadcast[1:]:
        lines.append(
            f"  [{event['category']} · {_age(event)}]: \"{event['content'][:130]}\""
        )
    return "\n".join(lines)


def interrupt(source: str, content: str, category: str = "general"):
    """High-salience write — forces this event to the top of focus (salience 0.95)."""
    write(source, content, salience=0.95, category=category)


def clear():
    """Flush all events — use only on session reset."""
    with _lock:
        _events.clear()
