"""
anima_micro.py — Continuous micro-cognition via a local tiny GGUF model.

Runs a small model on CPU every 10-20 seconds between full thoughts.
Generates fragments and associations — the background hum of mind.
These never go directly to the user; they feed the workspace.

Set micro_model_path in anima_config.json to enable.
"""

import os
import json
import random
import threading
import time
from collections import deque
from datetime import datetime

import anima_config
import anima_state_manager as state_mgr

_MODEL_PATH: str = anima_config.get("micro_model_path", "")
_INTERVAL_MIN    = 10
_INTERVAL_MAX    = 20
_MAX_MICRO       = 100

_model   = None
_running = False
_thread  = None
_micro_thoughts: deque = deque(maxlen=_MAX_MICRO)
_lock = threading.Lock()


def _micro_file() -> str:
    try:
        from anima_path import MEMORY_DIR
    except ImportError:
        MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
    return os.path.join(MEMORY_DIR, "anima_micro_thoughts.json")


def _save():
    path = _micro_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(_micro_thoughts)[-_MAX_MICRO:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ [Micro/save] {e}", flush=True)


def _load_model() -> bool:
    global _model, _MODEL_PATH
    _MODEL_PATH = anima_config.get("micro_model_path", _MODEL_PATH)
    if not _MODEL_PATH or not os.path.exists(_MODEL_PATH):
        print(f"⚠️ [Micro] Model not found: {_MODEL_PATH!r} — set micro_model_path in anima_config.json", flush=True)
        return False
    try:
        from llama_cpp import Llama
        print(f"🧠 [Micro] Loading {os.path.basename(_MODEL_PATH)} on CPU...", flush=True)
        _model = Llama(
            model_path=_MODEL_PATH,
            n_ctx=512,
            n_threads=4,
            n_gpu_layers=0,
            verbose=False,
        )
        print("✅ [Micro] Tiny model ready", flush=True)
        return True
    except Exception as e:
        print(f"❌ [Micro] Failed to load model: {e}", flush=True)
        return False


_MICRO_MODES = [
    ("curious",       "A fleeting curiosity or wonder — noticing something interesting."),
    ("sensory",       "A pure sensory impression — light, sound, texture, warmth, colour."),
    ("playful",       "A whimsical or playful association — light, quick, a little cheeky."),
    ("observational", "A detached observation about the moment or surroundings."),
    ("introspective", "A brief, honest feeling about her own inner state — just noticing."),
    ("associative",   "A free word-association chain — one thing leading to another."),
    ("anticipatory",  "A small excitement or anticipation about something coming up."),
]
_MICRO_WEIGHTS = [2, 2, 2, 2, 1, 2, 2]


def _build_prompt() -> str:
    s       = state_mgr.get_all()
    name    = anima_config.get("companion_name", "Anima")
    mood    = s.get("mood", "neutral")
    will    = s.get("will_to_live", 0.8)

    will_label = (
        "energised" if will >= 0.85 else
        "steady"    if will >= 0.65 else
        "a little tired" if will >= 0.45 else
        "drained"
    )

    mode_name, mode_desc = random.choices(_MICRO_MODES, weights=_MICRO_WEIGHTS, k=1)[0]

    seed = ""
    if random.random() < 0.4:
        try:
            with open(_micro_file(), "r", encoding="utf-8") as f:
                thoughts = json.load(f)
            if thoughts:
                pool = thoughts[-5:] if len(thoughts) >= 5 else thoughts
                seed = random.choice(pool)["fragment"][:60]
        except Exception:
            pass

    now = datetime.now().strftime("%I:%M %p")

    return f"""<|im_start|>system
You are {name}'s subconscious. Generate one micro-thought: {mode_desc} It is a fragment, not a full sentence. 5-18 words maximum. No quotation marks. No explanation.<|im_end|>
<|im_start|>user
Time: {now}. Mood: {mood}. Energy: {will_label}. Mode: {mode_name}. Seed: "{seed}"

One micro-thought:<|im_end|>
<|im_start|>assistant
"""


def _generate() -> str | None:
    if _model is None:
        return None
    try:
        prompt = _build_prompt()
        out = _model(
            prompt,
            max_tokens=40,
            temperature=0.82,
            top_p=0.9,
            top_k=40,
            stop=["<|im_end|>", "\n\n", "<|im_start|>"],
            echo=False,
        )
        text = out["choices"][0]["text"].strip().split("<|")[0].strip()
        return text if len(text) > 3 else None
    except Exception as e:
        print(f"⚠️ [Micro] Generation failed: {e}", flush=True)
        return None


def generate_offline(prompt: str, max_tokens: int = 80) -> str | None:
    """Shared offline generator — reuses the loaded micro model for any background module."""
    if _model is None:
        return None
    try:
        out = _model(
            prompt,
            max_tokens=max_tokens,
            temperature=0.88,
            top_p=0.9,
            top_k=40,
            stop=["<|im_end|>", "\n\n", "<|im_start|>", "\nUser:", "\nAssistant:"],
            echo=False,
        )
        text = out["choices"][0]["text"].strip().split("<|")[0].strip()
        return text if len(text) > 5 else None
    except Exception as e:
        print(f"⚠️ [Micro/offline] {e}", flush=True)
        return None


def get_recent(n: int = 5) -> list:
    with _lock:
        data = list(_micro_thoughts)
    return data[-n:] if data else []


def format_for_prompt(n: int = 3) -> str:
    recent = get_recent(n)
    if not recent:
        return ""
    fragments = " / ".join(t["fragment"] for t in recent)
    return f"[Background hum — micro-thoughts beneath full awareness]: {fragments}"


def _loop():
    global _running
    if not _load_model():
        print("⚠️ [Micro] Shutting down — no model available", flush=True)
        _running = False
        return

    time.sleep(30)  # let server settle

    while _running:
        fragment = _generate()
        if fragment:
            entry = {"time": datetime.now().isoformat(), "fragment": fragment}
            with _lock:
                _micro_thoughts.append(entry)
            _save()

            try:
                import anima_workspace
                anima_workspace.write("micro", fragment, salience=0.25, category="micro")
            except Exception as e:
                print(f"⚠️ [Micro/workspace] {e}", flush=True)

            print(f"⚡ [Micro] {fragment}", flush=True)

        time.sleep(random.uniform(_INTERVAL_MIN, _INTERVAL_MAX))


def start():
    global _running, _thread
    if _running:
        return
    if not anima_config.get("micro_model_path", ""):
        print("⚠️ [Micro] micro_model_path not set in config — skipping", flush=True)
        return
    _running = True
    _thread  = threading.Thread(target=_loop, daemon=True, name="AnimaMicro")
    _thread.start()
    print("🧠 [Micro] Micro-cognition thread started", flush=True)


def stop():
    global _running
    _running = False
    print("🧠 [Micro] Micro-cognition stopped", flush=True)
