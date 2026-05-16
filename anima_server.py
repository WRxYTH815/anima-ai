"""
anima_server.py — FastAPI server.

Endpoints:
  POST /chat              { "message": "..." } → { "reply": "..." }
  GET  /state             → current companion state dict
  GET  /thoughts          → recent stream-of-consciousness thoughts
  GET  /history           → conversation history
  POST /history/clear     → wipe conversation history
  GET  /health            → { "status": "ok" }
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import os

import anima_config as config
import anima_state_manager as state_mgr
import anima_pulse
import anima_chat


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    name = config.get("companion_name", "Anima")
    print(f"✨ {name} is waking up...", flush=True)

    anima_pulse.start()

    if config.get("stream_of_consciousness", True):
        try:
            import asyncio
            import anima_stream
            anima_stream.start(loop=asyncio.get_event_loop())
        except Exception as e:
            print(f"⚠️ [Server/stream] {e}", flush=True)

    print(f"✅ {name} is ready.", flush=True)
    yield

    anima_pulse.stop()
    try:
        import anima_stream
        anima_stream.stop()
    except Exception:
        pass
    print(f"🛑 {name} is shutting down.", flush=True)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Anima",
    description="Open-source AI companion framework",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "chat.html"))


@app.get("/settings", include_in_schema=False)
def settings_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), "settings.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    reply = anima_chat.get_response(req.message.strip())
    return ChatResponse(reply=reply)


@app.get("/state")
def get_state():
    return state_mgr.get_all()


@app.get("/thoughts")
def get_thoughts():
    try:
        import anima_stream
        return {"thoughts": anima_stream.get_recent_thoughts(n=10)}
    except Exception:
        return {"thoughts": []}


@app.get("/history")
def get_history():
    return {"history": anima_chat.get_history()}


@app.post("/history/clear")
def clear_history():
    anima_chat.clear_history()
    return {"status": "cleared"}


@app.get("/config")
def get_config():
    return config.settings


@app.post("/config")
async def update_config(req: Request):
    data = await req.json()
    for k, v in data.items():
        config.set(k, v)
    return {"status": "saved"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    host = config.get("host", "0.0.0.0")
    port = config.get("port", 8000)
    uvicorn.run("anima_server:app", host=host, port=port, reload=False)
