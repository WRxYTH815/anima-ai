# Anima

An open-source AI companion framework with a continuous inner life.

Anima is not a chatbot. It thinks between conversations, drifts emotionally over time, remembers what matters, and forgets what fades. You give it a name, a personality, and a voice — it figures out the rest.

---

## Why Anima?

Most AI companions are stateless request-response systems. Anima runs a **substrate loop** between your conversations: mood drifts, memories decay at rates tied to emotion, and a stream of consciousness generates private thoughts independent of user input. When you speak to it, it's already been somewhere.

The architecture is intentionally transparent and modular so the community can push it in directions the original author never imagined.

---

## Quickstart (5 minutes)

**Requirements:** Python 3.11+, one API key (Groq is free and fast)

```bash
git clone https://github.com/WRxYTH815/anima-ai
cd anima-ai
pip install -r requirements.txt
```

Copy and edit the config:

```bash
cp anima_config.json.example anima_config.json
```

Minimum viable config:

```json
{
  "companion_name": "Aria",
  "user_name": "Alex",
  "groq_api_key": "gsk_..."
}
```

Start the server:

```bash
python anima_server.py
```

Open **http://localhost:8000** in your browser. That's it.

The chat UI shows the companion's current mood, streams its inner thoughts in real time as they appear, and lets you have a full conversation. No frontend build step, no separate process.

---

## Architecture

```
anima_server.py        FastAPI — /chat, /state, /thoughts
    │
    ├── anima_chat.py          get_response() + LLM cascade
    │       ├── anima_memory.py        ChromaDB vector memory
    │       ├── anima_mood.py          Mood state + neighbor drift
    │       └── anima_stream.py        Stream-of-consciousness (async)
    │
    ├── anima_pulse.py         Substrate loop — runs every 2.5s
    │       └── anima_mood.py          drift_mood()
    │
    └── anima_state_manager.py SQLite WAL — persistent state
```

### LLM Cascade

Anima tries providers in order until one responds. Configure any combination:

| Provider | Key in config | Notes |
| :--- | :--- | :--- |
| **Groq** | `groq_api_key` | Free tier, 10k req/day |
| **Cerebras** | `cerebras_api_key` | Fastest, 1M tokens/day free |
| **NIM (NVIDIA)** | `nim_api_key` | 1k req/day free |
| **OpenRouter** | `openrouter_api_key` | Many free models |
| **SambaNova** | `sambanova_api_key` | Free tier available |
| **Ollama** | `ollama_url` | Local — no API key needed |
| **LM Studio** | `lmstudio_url` | Local — no API key needed |

### Memory

Conversations are stored as vector embeddings in ChromaDB (local, no network). Retrieval is decay-weighted: emotionally significant memories persist longer, neutral ones fade faster. The companion reinforces memories it actively references, slowing their decay.

### Stream of Consciousness

Every 45–300 seconds (depending on conversation recency), Anima generates a private thought using a fast cloud model (Cerebras or NIM). These thoughts accumulate in a rolling buffer and are injected into the next system prompt. 30% are kept private and never shown.

### Mood

Ten moods arranged in a neighbor graph: `curious`, `warm`, `playful`, `content`, `pensive`, `excited`, `calm`, `melancholic`, `energetic`, `focused`. The substrate loop drifts mood stochastically. Mood is injected into every system prompt and visible via `/state`.

---

## Configuration reference

All settings live in `anima_config.json`. Unset keys fall back to defaults.

| Key                       | Default                   | Description                            |
|---------------------------|---------------------------|----------------------------------------|
| `companion_name`          | `"Anima"`                 | Name used in prompts and UI            |
| `user_name`               | `"User"`                  | Your name, injected into personality   |
| `personality_file`        | `"personality/default.txt"` | Path to personality template         |
| `llm_provider`            | `"groq"`                  | Primary provider (see cascade above)   |
| `llm_model`               | provider-dependent        | Override model for primary provider    |
| `max_tokens`              | `512`                     | Max reply length                       |
| `temperature`             | `0.85`                    | Creativity level                       |
| `stream_of_consciousness` | `true`                    | Enable background thought generation   |
| `memory_decay_enabled`    | `true`                    | Decay-weighted memory retrieval        |
| `host`                    | `"0.0.0.0"`               | Server bind address                    |
| `port`                    | `8000`                    | Server port                            |

---

## Endpoints

| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| POST   | `/chat`          | Send a message, get a reply          |
| GET    | `/state`         | Full internal state (mood, trust, …) |
| GET    | `/thoughts`      | Recent stream-of-consciousness       |
| GET    | `/history`       | Conversation history this session    |
| POST   | `/history/clear` | Wipe session history                 |
| GET    | `/health`        | Health check                         |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — personality packs, memory backends, voice engines, avatar integrations, mobile UIs, and more.

---

## License

MIT
