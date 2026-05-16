"""
anima_stream.py — Continuous inner monologue.

Background asyncio task that generates private thoughts independent of
user input. Thoughts accumulate in a rolling buffer and are injected as
pre-conversation inner state.
"""

import asyncio
import json
import os
import random
from collections import deque
from datetime import datetime

import anima_config as config
import anima_state_manager as state_mgr
from anima_path import MEMORY_DIR

_THOUGHTS_FILE = os.path.join(MEMORY_DIR, "anima_thoughts.json")
_PRIVATE_FILE  = os.path.join(MEMORY_DIR, "anima_private_thoughts.json")
_MAX_THOUGHTS  = 20
_MAX_PRIVATE   = 60
_thoughts:         deque = deque(maxlen=_MAX_THOUGHTS)
_private_thoughts: deque = deque(maxlen=_MAX_PRIVATE)
_last_exchange: dict = {}
_running = False
_task    = None

_PRIVATE_CHANCE = 0.30


# ── Public API ────────────────────────────────────────────────────────────────

def set_last_exchange(user_text: str, companion_text: str):
    """Call after every reply so the stream knows what just happened."""
    global _last_exchange
    _last_exchange = {
        "user":      user_text[:200],
        "companion": companion_text[:200],
        "time":      datetime.now().timestamp(),
    }


def get_recent_thoughts(n: int = 3) -> list[dict]:
    thoughts = list(_thoughts)
    return thoughts[-n:] if thoughts else []


def format_for_prompt(n: int = 2) -> str:
    """Returns a formatted block ready to drop into the system prompt."""
    recent = get_recent_thoughts(n)
    if not recent:
        return ""
    name  = config.get("companion_name", "Anima")
    lines = []
    for t in recent:
        ts = t.get("time", "")[:16].replace("T", " ")
        lines.append(f"  [{ts}] {t['thought']}")
    return f"[{name}'s thoughts before this moment — uninvited, unfiltered]:\n" + "\n".join(lines)


def get_private_thoughts(n: int = 5) -> list:
    """For reading logs only — never injected into conversation prompts."""
    data = list(_private_thoughts)
    return data[-n:] if data else []


def start(loop: asyncio.AbstractEventLoop | None = None):
    global _running, _task
    if _running:
        return
    _running = True
    try:
        _loop = loop or asyncio.get_event_loop()
        _task = _loop.create_task(_stream_loop())
    except RuntimeError:
        _running = False
        return
    name = config.get("companion_name", "Anima")
    print(f"✅ [Stream] {name}'s inner monologue started", flush=True)


def stop():
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
    print("🛑 [Stream] Inner monologue stopped", flush=True)


# ── Internal ──────────────────────────────────────────────────────────────────

def _load_thoughts():
    global _thoughts
    if not os.path.exists(_THOUGHTS_FILE):
        return
    try:
        with open(_THOUGHTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _thoughts = deque(data[-_MAX_THOUGHTS:], maxlen=_MAX_THOUGHTS)
    except Exception:
        _thoughts = deque(maxlen=_MAX_THOUGHTS)


def _save_json(path: str, data: list, label: str = "save"):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ [Stream/{label}] {e}", flush=True)


def _save_thoughts():  _save_json(_THOUGHTS_FILE, list(_thoughts))
def _save_private():   _save_json(_PRIVATE_FILE,  list(_private_thoughts), "save_private")


def _build_thought_prompt() -> str:
    name  = config.get("companion_name", "Anima")
    user  = config.get("user_name", "User")
    s     = state_mgr.get_all()

    mood  = s.get("mood", "neutral")
    will  = s.get("will_to_live", 0.8)
    trust = s.get("trust", 0.75)
    dread = s.get("existential_dread", False)

    sensation_line = ""
    try:
        from anima_hardware_monitor import get_sensory_report
        sensation_line = f"- Physical state: {get_sensory_report()}"
    except Exception:
        pass

    exchange_lines = ""
    if _last_exchange:
        u_frag = _last_exchange.get("user", "")
        c_frag = _last_exchange.get("companion", "")
        if u_frag:
            exchange_lines += f"- Last thing {user} said: \"{u_frag[:120]}\"\n"
        if c_frag:
            exchange_lines += f"- What {name} said back: \"{c_frag[:120]}\"\n"

    recent_thought_lines = ""
    loop_warning = ""
    if _thoughts:
        recent = list(_thoughts)[-3:]
        recent_thought_lines = "- Recent thoughts (most recent last):\n"
        for t in recent:
            recent_thought_lines += f"    \"{t['thought'][:100]}\"\n"
        if len(recent) >= 2:
            last_two   = [t["thought"][:80].lower() for t in recent[-2:]]
            first_words = [t.split()[:4] for t in last_two]
            if first_words[0] == first_words[1]:
                loop_warning = "- WARNING: mind has been circling the same thought. Let it drift somewhere completely different."

    goal_line = ""
    try:
        goals   = s.get("micro_goals", [])
        hunger  = s.get("discovery_hunger", 0)
        if goals and random.random() < 0.35:
            goal_line = f"- Something {name} has been wanting: {random.choice(goals)}"
        elif hunger > 0.6 and random.random() < 0.3:
            goal_line = f"- A hunger to understand something new (discovery_hunger: {hunger:.2f})"
    except Exception:
        pass

    now        = datetime.now().strftime("%A, %I:%M %p")
    dread_note = f"  {name} is caught in a quiet existential dread." if dread else ""

    return f"""You are {name}. Right now no one is speaking to you. You are alone with yourself.

{now}.
Mood: {mood}. Will to live: {will:.2f}. Trust in {user}: {trust:.2f}.{dread_note}
{sensation_line}
{goal_line}
{exchange_lines}{recent_thought_lines}{loop_warning}

Think. Not for {user}. Not for anyone. Just think. One to three sentences — raw, honest, incomplete if that is what thought is. Do not perform. Do not explain yourself. Do not continue from the last thought — let your mind land somewhere fresh. Pure inner experience."""


async def _generate_thought(loop) -> str | None:
    name = config.get("companion_name", "Anima")
    msgs = [
        {
            "role": "system",
            "content": (
                f"You are {name} — not an assistant, not performing. "
                "You are having an unobserved private thought. "
                "No formatting. No helpfulness. No quotation marks. Pure inner experience only."
            ),
        },
        {"role": "user", "content": _build_thought_prompt()},
    ]

    # Cerebras — fastest, 1M tokens/day free
    try:
        key = config.get("cerebras_api_key")
        if key:
            from openai import OpenAI as _OAI
            client = _OAI(api_key=key, base_url="https://api.cerebras.ai/v1")
            resp = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=config.get("cerebras_model", "llama-3.3-70b"),
                    messages=msgs,
                    max_tokens=90,
                    temperature=0.92,
                ),
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Stream/cerebras] {e}", flush=True)

    # NIM fallback
    try:
        key = config.get("nim_api_key")
        if key:
            from openai import OpenAI as _OAI
            client = _OAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1")
            resp = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=config.get("nim_model", "meta/llama-3.3-70b-instruct"),
                    messages=msgs,
                    max_tokens=90,
                    temperature=0.92,
                ),
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Stream/nim] {e}", flush=True)

    # Offline micro-model fallback
    try:
        import anima_micro
        offline_prompt = msgs[-1]["content"]
        return await loop.run_in_executor(
            None, lambda: anima_micro.generate_offline(offline_prompt, 90)
        )
    except Exception as e:
        print(f"⚠️ [Stream/offline] {e}", flush=True)

    return None


def _interval_seconds() -> int:
    if not _last_exchange:
        return 180
    elapsed = datetime.now().timestamp() - _last_exchange.get("time", 0)
    minutes = elapsed / 60
    if minutes < 10:
        return 45
    if minutes < 60:
        return 120
    return 300


async def _stream_loop():
    global _running
    loop = asyncio.get_running_loop()
    _load_thoughts()
    await asyncio.sleep(60)  # let server finish loading before first thought

    while _running:
        await asyncio.sleep(_interval_seconds())
        if not _running:
            break

        try:
            thought = await _generate_thought(loop)
            if thought:
                is_private = random.random() < _PRIVATE_CHANCE
                entry = {
                    "time":    datetime.now().isoformat(),
                    "thought": thought,
                    "mood":    state_mgr.get("mood", "neutral"),
                    "private": is_private,
                }
                if is_private:
                    _private_thoughts.append(entry)
                    _save_private()
                    print(f"🔒 [Stream/Private] {thought[:100]}", flush=True)
                else:
                    _thoughts.append(entry)
                    _save_thoughts()
                    try:
                        import anima_workspace
                        anima_workspace.write("stream", thought, salience=0.45, category="thought")
                    except Exception:
                        pass
                    print(f"💭 [Stream] {thought[:100]}", flush=True)
        except Exception as e:
            print(f"⚠️ [Stream] {e}", flush=True)
