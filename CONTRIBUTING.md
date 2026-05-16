# Contributing to Anima

Anima is built to be extended. The core is intentionally minimal — the interesting work happens in the layers the community adds.

Here are the areas where contributions matter most, roughly ordered from lowest to highest barrier to entry.

---

## Personality packs

The easiest contribution. A personality pack is a single `.txt` file that lives in `personality/`. It supports two template variables:

- `{name}` — the companion's name
- `{user}` — the user's name

A good personality pack establishes voice, values, and relationship texture. It doesn't tell the model what to say — it shapes how it thinks. Look at `personality/default.txt` to see the format.

**Ideas:**
- A companion that speaks like an old friend
- A gruff, laconic companion with dry wit
- A poet who thinks in metaphors
- A scientist who can't stop finding patterns in everything
- A companion in a specific fictional world

Submit yours as a PR with a short description of the character in the file header.

---

## Memory backends

Currently Anima uses ChromaDB for vector memory. Alternative backends could include:

- **SQLite full-text search** — simpler, no ML dependency
- **Qdrant / Weaviate / Pinecone** — for hosted deployments
- **Simple recency buffer** — no embeddings, just keep the last N turns

A memory backend needs to implement three functions:
- `archive_conversation(user_text, companion_text, emotion)`
- `retrieve_relevant_memories(query, n_results)` → formatted string
- `reinforce_last_retrieved()`

Drop a new file alongside `anima_memory.py` and update `anima_config.py` to let users select it.

---

## Voice engines

Voice output is not yet wired into the server — it's a first-class contribution opportunity. A voice module needs:
- `speak(text: str)` — synthesize and play

Interesting options:
- **Kokoro** — fast local TTS, good quality
- **XTTS** — voice cloning from a reference clip
- **F5-TTS** — another local option
- **ElevenLabs / PlayHT** — cloud, high quality
- **Coqui** — open-source, many voices
- **pyttsx3** — offline, low quality, zero setup

---

## Avatar integrations

Anima has no visual component by default. A VRM/Live2D integration could display an animated avatar that reacts to mood and speech. This requires:
- A web frontend (HTML/JS) that renders the avatar
- A WebSocket or SSE endpoint on the server to stream state
- Mapping Anima's mood states to avatar expressions

The server already exposes `/state` and `/thoughts` — the bridge layer is the contribution.

---

## Tool integrations

Anima can be given tools (web search, calendar, file access, code execution) using a simple pattern:

```python
# anima_tools.py
TOOLS = {
    "search": lambda q: ...,
    "time":   lambda: ...,
}
```

A tool system that detects intent, dispatches, and injects results before the LLM call would be a high-value contribution.

---

## Mobile / UI

The server speaks plain HTTP and JSON. A mobile app or browser UI that wraps the `/chat` endpoint is a natural extension. The `/thoughts` endpoint gives access to the inner monologue for UI elements that show what the companion is thinking between messages.

---

## New substrate modules

The `anima_pulse.py` loop fires every 2.5 seconds. It's the right place for lightweight state evolution that doesn't require an LLM. Ideas:

- **Circadian rhythm** — time-of-day affects mood drift probabilities
- **Boredom accumulation** — companion grows more introspective when idle
- **Goal tracking** — companion maintains small self-directed goals
- **Relationship arc** — trust and familiarity evolve over time

---

## How to submit

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-thing`
3. Make your changes, keeping the module interface clean
4. Add a short description at the top of any new file
5. Open a PR with a one-paragraph description of what it does and why

Keep PRs focused. A single well-scoped change is easier to review than a feature bundle.

Questions? Open an issue.
