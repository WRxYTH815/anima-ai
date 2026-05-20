"""
anima_wiki.py — LLM-maintained persistent knowledge wiki.

Inspired by Andrej Karpathy's LLM-wiki pattern (April 2026):
instead of re-deriving facts on every query, the LLM maintains
a growing collection of markdown pages. Pages are updated on ingest,
queried for context, and linted periodically for contradictions.

Wiki lives in memory/wiki/*.md — human-readable, version-controllable.

Three operations:
  ingest(text)   — LLM extracts facts, creates/updates pages
  query(text)    — keyword-match relevant pages for prompt context
  lint()         — LLM periodic health check, fixes contradictions
"""

import json
import os
import threading
import time

import anima_config as config

_WIKI_DIR: str | None = None
_LINT_INTERVAL = 3600 * 6   # lint every 6 hours
_running = False
_thread: threading.Thread | None = None
_lock    = threading.Lock()
_exchange_count = 0          # ingest every 5th exchange


def _get_dir() -> str:
    global _WIKI_DIR
    if _WIKI_DIR:
        return _WIKI_DIR
    try:
        from anima_path import MEMORY_DIR
        _WIKI_DIR = os.path.join(MEMORY_DIR, "wiki")
    except Exception:
        _WIKI_DIR = os.path.join(os.path.dirname(__file__), "memory", "wiki")
    os.makedirs(_WIKI_DIR, exist_ok=True)
    return _WIKI_DIR


def _list_pages() -> list[str]:
    return [f for f in os.listdir(_get_dir()) if f.endswith(".md")]


def _read_page(name: str) -> str:
    path = os.path.join(_get_dir(), name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _write_page(name: str, content: str):
    with open(os.path.join(_get_dir(), name), "w", encoding="utf-8") as f:
        f.write(content)


def _llm(msgs: list) -> str | None:
    try:
        import anima_chat
        return anima_chat._call_llm(msgs)
    except Exception as e:
        print(f"⚠️ [Wiki/llm] {e}", flush=True)
        return None


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest(source_text: str):
    """
    LLM reads source_text and creates/updates relevant wiki pages.
    Capped at 3 page-writes per call to stay fast.
    Called every 5 exchanges from anima_chat._post_exchange().
    """
    global _exchange_count
    _exchange_count += 1
    if _exchange_count % 5 != 0:
        return

    if not source_text.strip():
        return

    name  = config.get("companion_name", "Anima")
    user  = config.get("user_name", "User")
    pages = _list_pages()
    index = _read_page("INDEX.md") or "*(empty wiki)*"
    page_list = "\n".join(f"- {p}" for p in pages if p != "INDEX.md") or "*(none)*"

    system = (
        f"You are the knowledge curator for {name}'s persistent wiki. "
        f"The wiki stores facts about {user}, {name}, and their shared world. "
        f"Respond ONLY with valid JSON — no explanation, no markdown fences."
    )
    user_msg = f"""Existing pages:
{page_list}

Index:
{index}

New exchange to process:
{source_text[:1200]}

Extract meaningful, lasting facts (preferences, interests, personal details, notable events).
Skip small-talk. If nothing meaningful, respond with [].

Respond with a JSON array (max 3 items):
[
  {{"filename": "descriptive_name.md", "content": "# Title\\n\\nFacts here..."}},
  ...
]

Rules:
- Filenames: snake_case, .md, descriptive (e.g. user_hobbies.md, companion_growth.md)
- Each page: under 400 words, facts only, no speculation
- If updating INDEX.md, include it as one of the 3 items
"""

    with _lock:
        result = _llm([
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ])

    if not result:
        return

    try:
        start = result.find("[")
        end   = result.rfind("]") + 1
        if start == -1 or end <= 1:
            return
        pages_data = json.loads(result[start:end])
        for item in pages_data:
            fname   = str(item.get("filename", "")).strip()
            content = str(item.get("content",  "")).strip()
            if fname and content and fname.endswith(".md") and "/" not in fname:
                _write_page(fname, content)
                print(f"📖 [Wiki] Updated: {fname}", flush=True)
    except Exception as e:
        print(f"⚠️ [Wiki/ingest] {e}", flush=True)


# ── Query ─────────────────────────────────────────────────────────────────────

def query(question: str, n_pages: int = 2) -> str:
    """
    Keyword-match question against wiki pages.
    Returns relevant snippets for system prompt injection.
    No embeddings — simple word overlap score.
    """
    pages = [p for p in _list_pages() if p != "INDEX.md"]
    if not pages:
        return ""

    words  = [w for w in question.lower().split() if len(w) > 3]
    scored = []
    for fname in pages:
        content = _read_page(fname)
        score   = sum(1 for w in words if w in content.lower())
        if score > 0:
            scored.append((score, fname, content))

    if not scored:
        return ""

    scored.sort(reverse=True)
    parts = []
    for _, fname, content in scored[:n_pages]:
        parts.append(f"[Wiki — {fname[:-3].replace('_', ' ')}]: {content[:280].strip()}")
    return "\n".join(parts)


# ── Lint ──────────────────────────────────────────────────────────────────────

def lint():
    """
    Periodic LLM health check. Finds contradictions and duplicate facts,
    rewrites affected pages. Runs every 6 hours in background.
    """
    pages = [p for p in _list_pages() if p != "INDEX.md"]
    if len(pages) < 2:
        return

    name    = config.get("companion_name", "Anima")
    collated = ""
    for fname in pages[:8]:
        collated += f"\n\n--- {fname} ---\n{_read_page(fname)[:350]}"

    system   = f"You are the wiki linter for {name}. Respond ONLY with valid JSON."
    user_msg = f"""Review these wiki pages for contradictions or duplicated facts:
{collated}

If everything is consistent, respond with: {{"status": "ok"}}

If there are issues to fix:
{{
  "status": "fixed",
  "pages": [
    {{"filename": "page.md", "content": "corrected content"}}
  ]
}}
"""
    result = _llm([
        {"role": "system", "content": system},
        {"role": "user",   "content": user_msg},
    ])
    if not result:
        return
    try:
        start = result.find("{")
        end   = result.rfind("}") + 1
        if start == -1:
            return
        data = json.loads(result[start:end])
        if data.get("status") == "fixed":
            for item in data.get("pages", []):
                fname   = str(item.get("filename", "")).strip()
                content = str(item.get("content",  "")).strip()
                if fname and content and fname.endswith(".md") and "/" not in fname:
                    _write_page(fname, content)
                    print(f"📖 [Wiki/lint] Fixed: {fname}", flush=True)
    except Exception as e:
        print(f"⚠️ [Wiki/lint] {e}", flush=True)


# ── Background loop ───────────────────────────────────────────────────────────

def _loop():
    time.sleep(120)   # 2-min warmup
    while _running:
        try:
            lint()
        except Exception as e:
            print(f"⚠️ [Wiki/loop] {e}", flush=True)
        time.sleep(_LINT_INTERVAL)


def start():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread  = threading.Thread(target=_loop, daemon=True, name="AnimaWiki")
    _thread.start()
    print("📖 [Wiki] Knowledge base started", flush=True)


def stop():
    global _running
    _running = False
