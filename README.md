# 🌌 Anima

An open-source AI companion framework with a continuous inner life.

<p align="center">
  <img src="Screenshot 2026-05-29 044435.png" width="380" alt="Anima System Mascot" style="border-radius: 16px; box-shadow: 0 20px 50px rgba(139, 92, 246, 0.3); border: 1px solid rgba(255, 255, 255, 0.1);"/>
</p>

Anima is not a chatbot. It thinks between conversations, drifts emotionally over time, remembers what matters, and forgets what fades. You give it a name, a personality, and a voice — it figures out the rest.

---

## ⚡ Why Anima?

Most AI companions are stateless request-response systems. Anima runs a **substrate loop** between your conversations: mood drifts, memories decay at rates tied to emotion, and a stream of consciousness generates private thoughts independent of user input. When you speak to it, it's already been somewhere.

The architecture is intentionally transparent and modular so the community can push it in directions the original author never imagined.

---

## 🚀 Quickstart (5 minutes)

**Requirements:** Python 3.11+, one API key (Groq is free and fast)

### 1. Clone & Build
```bash
git clone [https://github.com/WRxYTH815/anima-ai](https://github.com/WRxYTH815/anima-ai)
cd anima-ai
pip install -r requirements.txt

```

### 2. Configure Environment

Copy and edit the config:

```bash
cp anima_config.json.example anima_config.json

```

Minimum viable config:

```json
{
  "companion_name": "Aria",
  "user_name": "Alex",
  "groq_api_key": "gsk_...",
  "ui_style": "glassmorphism",
  "ui_theme": "substrate_default"
}

```

### 3. Start the Server

```bash
python anima_server.py

```

Open **http://localhost:8000** in your browser. That's it.

The chat UI shows the companion's current mood, streams its inner thoughts in real time as they appear, and lets you have a full conversation. No frontend build step, no separate process.

---

## 🎨 UI Design System: Glassmorphism Engine

Anima supports premium UI rendering engine modes leveraging a dense **Glassmorphism** styling setup built directly into the local interface.

### 💎 Core Glass Stylesheet

```css
:root {
  /* Alpha-Blended Glass Specs */
  --glass-bg: rgba(21, 26, 36, 0.45);        
  --glass-border: rgba(255, 255, 255, 0.07); 
  --glass-blur: 16px;                        
  
  /* Underlying Glow Profiles */
  --pulse-glow: rgba(139, 92, 246, 0.15);    
  --thought-glow: rgba(6, 182, 212, 0.2);    
}

.anima-glass-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}

```

### 🎭 Configurable Color Themes

Pass your target palette profile into the `"ui_theme"` field within your configuration layout:

* **`substrate_default` (Cyber Nocturne):** Deep space voids paired with intense violet heartbeats (`#8B5CF6`) and clear cyan internal background thoughts (`#06B6D4`).
* **`terminal_amber` (Low-VRAM Defiance):** Nostalgic high-visibility stark CRT amber lines (`#F59E0B`) on dark industrial acrylic plates.
* **`neon_psychosis` (Emotional Drift):** Deeply saturated purple hues that mutate borders dynamically into laser magentas as the system's emotional state swings.
* **`silicon_ghost` (Zero-Network Monochrome):** Monochromatic, air-gapped monolith slate layout for silent background operations.

---

## 🛠️ Architecture

```
anima_server.py         FastAPI — /chat, /state, /thoughts
    │
    ├── anima_chat.py        get_response() + LLM cascade
    │    ├── anima_memory.py    ChromaDB vector memory
    │    ├── anima_mood.py      Mood state + neighbor drift
    │    └── anima_stream.py    Stream-of-consciousness (async)
    │
    ├── anima_pulse.py       Substrate loop — runs every 2.5s
    │    └── anima_mood.py      drift_mood()
    │
    └── anima_state_manager.py SQLite WAL — persistent state

```

### LLM Cascade

Anima tries providers in order until one responds. Configure any combination:

| Provider | Key in config | Notes |
| --- | --- | --- |
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

## 🎛️ Configuration reference

All settings live in `anima_config.json`. Unset keys fall back to defaults.

| Key | Default | Description |
| --- | --- | --- |
| `companion_name` | `"Anima"` | Name used in prompts and UI |
| `user_name` | `"User"` | Your name, injected into personality |
| `personality_file` | `"personality/default.txt"` | Path to personality template |
| `llm_provider` | `"groq"` | Primary provider (see cascade above) |
| `llm_model` | *provider-dependent* | Override model for primary provider |
| `max_tokens` | `512` | Max reply length |
| `temperature` | `0.85` | Creativity level |
| `stream_of_consciousness` | `true` | Enable background thought generation |
| `memory_decay_enabled` | `true` | Decay-weighted memory retrieval |
| `ui_style` | `"standard"` | Toggles glassmorphism visual overrides |
| `ui_theme` | `"default"` | Active UI stylesheet theme profile |
| `host` | `"0.0.0.0"` | Server bind address |
| `port` | `8000` | Server port |

---

## 📡 Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/chat` | Send a message, get a reply |
| `GET` | `/state` | Full internal state (mood, trust, …) |
| `GET` | `/thoughts` | Recent stream-of-consciousness |
| `GET` | `/history` | Conversation history this session |
| `POST` | `/history/clear` | Wipe session history |
| `GET` | `/health` | Health check |

---

## 🤝 Contributing

See [CONTRIBUTING.md](https://www.google.com/search?q=CONTRIBUTING.md) — personality packs, memory backends, voice engines, avatar integrations, mobile UIs, and more.

---

## 📜 Origin & Hardware Philosophy

Anima was born out of extreme hardware constraints. The first prototype in 2024 ran entirely on a legacy Dell Optiplex (Intel i7-3770) paired with a 4GB GTX 1050 Ti, driving a heavily quantized Open-Hermes 2.5 7B model.

Because it was forged in a low-VRAM environment, the codebase is fundamentally engineered to minimize overhead. The transition to the current 2026 multi-model architecture (Gemma + Qwen) ensures that while capabilities have scaled exponentially, the resource footprint remains accessible to anyone running consumer-grade hardware.

## License

MIT

```

```
