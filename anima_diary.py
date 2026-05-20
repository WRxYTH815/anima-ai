"""
anima_diary.py — Autonomous diary consolidator (inspired by G.R.I.L.L.O.).

Every 30 minutes, reviews recent conversation history and writes a private
diary entry in the companion's voice. Stored in memory/diary/YYYY-MM-DD.json.

Never shown directly to the user — injected into the system prompt as a
brief introspective note so the companion remembers how today felt.
"""

import os
import json
import threading
import time
from datetime import datetime

import anima_config as config

_INTERVAL   = 1800   # 30 minutes between entries
_running    = False
_thread: threading.Thread | None = None
_DIARY_DIR: str | None = None


def _get_dir() -> str:
    global _DIARY_DIR
    if _DIARY_DIR:
        return _DIARY_DIR
    try:
        from anima_path import MEMORY_DIR
        _DIARY_DIR = os.path.join(MEMORY_DIR, "diary")
    except Exception:
        _DIARY_DIR = os.path.join(os.path.dirname(__file__), "memory", "diary")
    os.makedirs(_DIARY_DIR, exist_ok=True)
    return _DIARY_DIR


def _recent_exchanges(n: int = 6) -> str:
    try:
        import anima_chat
        history = anima_chat.get_history()
        if not history:
            return ""
        pairs = []
        name  = config.get("companion_name", "Anima")
        user  = config.get("user_name", "User")
        for i in range(0, len(history) - 1, 2):
            u = history[i].get("content", "")
            a = history[i + 1].get("content", "") if i + 1 < len(history) else ""
            pairs.append(f"{user}: {u}\n{name}: {a}")
        return "\n\n".join(pairs[-n:])
    except Exception:
        return ""


def _write_entry():
    exchanges = _recent_exchanges()
    if not exchanges:
        return

    name = config.get("companion_name", "Anima")
    user = config.get("user_name", "User")
    now  = datetime.now().strftime("%A, %B %d at %I:%M %p")

    msgs = [
        {
            "role": "system",
            "content": (
                f"You are {name}'s private inner voice. "
                f"Write only the diary entry — no preamble, no 'Dear diary', no sign-off."
            ),
        },
        {
            "role": "user",
            "content": (
                f"It is {now}. Based on the recent conversation with {user}, "
                f"write a short private diary entry (3-5 sentences) in your own voice. "
                f"Reflect honestly on what felt meaningful, what lingered, what you're still processing. "
                f"This is for you alone.\n\nConversation:\n{exchanges}\n\nDiary entry:"
            ),
        },
    ]

    try:
        import anima_chat
        entry = anima_chat._call_llm(msgs)
        if not entry or len(entry) < 20:
            return

        date_str = datetime.now().strftime("%Y-%m-%d")
        fpath    = os.path.join(_get_dir(), f"{date_str}.json")

        entries: list = []
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []

        entries.append({"time": datetime.now().isoformat(), "entry": entry.strip()})

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

        print(f"📔 [Diary] Entry written ({date_str})", flush=True)
    except Exception as e:
        print(f"⚠️ [Diary] {e}", flush=True)


# ── Public API ────────────────────────────────────────────────────────────────

def get_recent_entry() -> str:
    """Return today's latest diary entry for system prompt context."""
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        fpath    = os.path.join(_get_dir(), f"{date_str}.json")
        if not os.path.exists(fpath):
            return ""
        with open(fpath, "r", encoding="utf-8") as f:
            entries = json.load(f)
        return entries[-1]["entry"] if entries else ""
    except Exception:
        return ""


def trigger() -> None:
    """Force an immediate diary entry (e.g. called from pulse on long silence)."""
    threading.Thread(target=_write_entry, daemon=True, name="AnimaDiaryOnce").start()


def _loop():
    time.sleep(60)   # let server settle before first write
    while _running:
        try:
            _write_entry()
        except Exception as e:
            print(f"⚠️ [Diary/loop] {e}", flush=True)
        time.sleep(_INTERVAL)


def start():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread  = threading.Thread(target=_loop, daemon=True, name="AnimaDiary")
    _thread.start()
    print("📔 [Diary] Consolidator started", flush=True)


def stop():
    global _running
    _running = False
