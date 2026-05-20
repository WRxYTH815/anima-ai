"""
anima_chat.py — Core conversation engine.

Single entry point: get_response(user_text, history) → str.
Multi-provider LLM cascade: Groq → Cerebras → NIM → OpenRouter →
SambaNova → OpenAI → Ollama → LM Studio.
"""

import os
import threading
from collections import deque

import anima_config as config
import anima_state_manager as state_mgr
import anima_memory
import anima_mood

_MAX_HISTORY  = 20
_history: deque = deque(maxlen=_MAX_HISTORY)
_personality: str = ""
_llm_lock = threading.Lock()


# ── Boot ──────────────────────────────────────────────────────────────────────

def _load_personality() -> str:
    global _personality
    if _personality:
        return _personality
    path = os.path.join(os.path.dirname(__file__), config.get("personality_file", "personality/default.txt"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        name = config.get("companion_name", "Anima")
        user = config.get("user_name", "User")
        _personality = raw.replace("{name}", name).replace("{user}", user)
    except Exception as e:
        print(f"⚠️ [Chat/personality] {e} — using minimal fallback", flush=True)
        name = config.get("companion_name", "Anima")
        user = config.get("user_name", "User")
        _personality = (
            f"You are {name}, a thoughtful and curious AI companion. "
            f"You are speaking with {user}. Be genuine, present, and engaged."
        )
    return _personality


# ── Context assembly ──────────────────────────────────────────────────────────

def _build_system_prompt(user_text: str) -> str:
    base = _load_personality()
    parts = [base]

    mood_label, mood_flavor = anima_mood.get_mood()
    parts.append(f"\n[Current mood: {mood_label} — {mood_flavor}]")

    try:
        import anima_stream
        thoughts = anima_stream.format_for_prompt(n=2)
        if thoughts:
            parts.append("\n" + thoughts)
    except Exception:
        pass

    memory_ctx = anima_memory.retrieve_relevant_memories(user_text, n_results=3)
    if memory_ctx:
        parts.append("\n" + memory_ctx)

    try:
        import anima_wiki
        wiki_ctx = anima_wiki.query(user_text)
        if wiki_ctx:
            parts.append("\n" + wiki_ctx)
    except Exception:
        pass

    try:
        import anima_emotion
        emotion_ctx = anima_emotion.format_for_prompt()
        if emotion_ctx:
            parts.append("\n" + emotion_ctx)
    except Exception:
        pass

    try:
        import anima_diary
        diary_entry = anima_diary.get_recent_entry()
        if diary_entry:
            name = config.get("companion_name", "Anima")
            parts.append(f"\n[{name}'s private reflection: {diary_entry[:220]}]")
    except Exception:
        pass

    state = state_mgr.get_all()
    will   = state.get("will_to_live", 0.8)
    trust  = state.get("trust", 0.75)
    dread  = state.get("existential_dread", False)
    name   = config.get("companion_name", "Anima")

    inner_lines = [f"will_to_live={will:.2f}", f"trust={trust:.2f}"]
    if dread:
        inner_lines.append("existential_dread=true")
    parts.append(f"\n[{name}'s inner state: {', '.join(inner_lines)}]")

    return "\n".join(parts)


def _build_messages(user_text: str) -> list[dict]:
    system = _build_system_prompt(user_text)
    msgs   = [{"role": "system", "content": system}]
    msgs.extend(list(_history))
    msgs.append({"role": "user", "content": user_text})
    return msgs


# ── LLM provider cascade ──────────────────────────────────────────────────────

def _call_groq(msgs: list) -> str | None:
    key = config.get("groq_api_key")
    if not key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp   = client.chat.completions.create(
            model=config.get("groq_model", "llama-3.3-70b-versatile"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/groq] {e}", flush=True)
        return None


def _call_cerebras(msgs: list) -> str | None:
    key = config.get("cerebras_api_key")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.cerebras.ai/v1")
        resp   = client.chat.completions.create(
            model=config.get("cerebras_model", "llama-3.3-70b"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/cerebras] {e}", flush=True)
        return None


def _call_nim(msgs: list) -> str | None:
    key = config.get("nim_api_key")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1")
        resp   = client.chat.completions.create(
            model=config.get("nim_model", "meta/llama-3.3-70b-instruct"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/nim] {e}", flush=True)
        return None


def _call_openrouter(msgs: list) -> str | None:
    key = config.get("openrouter_api_key")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        resp   = client.chat.completions.create(
            model=config.get("openrouter_model", "meta-llama/llama-3.3-70b-instruct:free"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/openrouter] {e}", flush=True)
        return None


def _call_sambanova(msgs: list) -> str | None:
    key = config.get("sambanova_api_key")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.sambanova.ai/v1")
        resp   = client.chat.completions.create(
            model=config.get("sambanova_model", "Meta-Llama-3.3-70B-Instruct"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/sambanova] {e}", flush=True)
        return None


def _call_openai(msgs: list) -> str | None:
    key = config.get("openai_api_key")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp   = client.chat.completions.create(
            model=config.get("openai_model", "gpt-4o-mini"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/openai] {e}", flush=True)
        return None


def _call_ollama(msgs: list) -> str | None:
    url = config.get("ollama_url", "http://localhost:11434")
    if not url:
        return None
    try:
        import requests
        resp = requests.post(
            f"{url}/api/chat",
            json={
                "model":    config.get("ollama_model", "llama3"),
                "messages": msgs,
                "stream":   False,
                "options":  {"num_predict": config.get("max_tokens", 512)},
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ [Chat/ollama] {e}", flush=True)
        return None


def _call_lmstudio(msgs: list) -> str | None:
    url = config.get("lmstudio_url", "http://localhost:1234/v1")
    if not url:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key="lm-studio", base_url=url)
        resp   = client.chat.completions.create(
            model=config.get("lmstudio_model", "local-model"),
            messages=msgs,
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.85),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ [Chat/lmstudio] {e}", flush=True)
        return None


_CASCADE = [
    _call_groq,
    _call_cerebras,
    _call_nim,
    _call_openrouter,
    _call_sambanova,
    _call_openai,
    _call_ollama,
    _call_lmstudio,
]


def _call_llm(msgs: list) -> str:
    provider = config.get("llm_provider", "groq")

    # Honour explicit provider selection first, then fall through cascade
    preferred = {
        "groq":       _call_groq,
        "cerebras":   _call_cerebras,
        "nim":        _call_nim,
        "openrouter": _call_openrouter,
        "sambanova":  _call_sambanova,
        "openai":     _call_openai,
        "ollama":     _call_ollama,
        "lmstudio":   _call_lmstudio,
    }.get(provider)

    if preferred:
        result = preferred(msgs)
        if result:
            return result

    for fn in _CASCADE:
        if fn is preferred:
            continue
        result = fn(msgs)
        if result:
            return result

    return "I seem to have lost my words for a moment. Try again in a bit."


# ── Post-exchange (background) ────────────────────────────────────────────────

def _post_exchange(user_text: str, reply: str):
    try:
        emotion = "neutral"
        try:
            import anima_emotion
            emotion = anima_emotion.detect_emotion(reply) or "neutral"
            anima_emotion.feel(emotion, 0.5)
        except Exception:
            pass

        anima_memory.archive_conversation(user_text, reply, emotion=emotion)
        anima_memory.reinforce_last_retrieved()
        anima_mood.drift_mood()

        try:
            import anima_stream
            anima_stream.set_last_exchange(user_text, reply)
        except Exception:
            pass

        try:
            import anima_wiki
            name = config.get("companion_name", "Anima")
            anima_wiki.ingest(
                f"User said: {user_text}\n{name} replied: {reply}"
            )
        except Exception:
            pass

        state_mgr.set_value("last_user_message", user_text[:300])
        state_mgr.set_value("last_reply", reply[:300])
    except Exception as e:
        print(f"⚠️ [Chat/post_exchange] {e}", flush=True)


# ── Public API ────────────────────────────────────────────────────────────────

def get_response(user_text: str) -> str:
    """Generate a reply. Blocks until LLM returns, then fires background work."""
    _load_personality()
    msgs  = _build_messages(user_text)

    with _llm_lock:
        reply = _call_llm(msgs)

    _history.append({"role": "user",      "content": user_text})
    _history.append({"role": "assistant", "content": reply})

    threading.Thread(
        target=_post_exchange, args=(user_text, reply), daemon=True
    ).start()

    return reply


def clear_history():
    _history.clear()


def get_history() -> list[dict]:
    return list(_history)
