import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "anima_config.json")

_DEFAULTS = {
    "companion_name": "Anima",
    "user_name": "User",
    "personality_file": "personality/default.txt",
    "llm_provider": "groq",
    "groq_api_key": "",
    "openai_api_key": "",
    "cerebras_api_key": "",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "lmstudio_url": "http://localhost:1234/v1",
    "llm_model": "llama-3.3-70b-versatile",
    "tts_provider": "kokoro",
    "xtts_reference_audio": "voices/reference.wav",
    "vrm_model": "vrm/default.vrm",
    "memory_decay_enabled": True,
    "stream_of_consciousness": True,
    "narrative_self": True,
    "hardware_profile": "auto",
}

def _load() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except FileNotFoundError:
        return dict(_DEFAULTS)
    except Exception as e:
        print(f"⚠️ [Config] Failed to load config: {e} — using defaults")
        return dict(_DEFAULTS)

settings = _load()


def get(key: str, default=None):
    return settings.get(key, default)


def reload():
    global settings
    settings = _load()


def save():
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ [Config] Failed to save config: {e}")


def set(key: str, value):
    settings[key] = value
    save()
