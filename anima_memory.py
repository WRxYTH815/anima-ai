"""
anima_memory.py — Persistent vector memory using ChromaDB.

Stores every conversation turn as an embedding so the companion
can recall relevant past context when answering future messages.
"""

import datetime
import uuid

from anima_path import CHROMA_DB_DIR
from anima_memory_decay import decay_score, get_half_life
import anima_config as config

_embed_fn           = None
_client             = None
_collection         = None
_last_retrieved_ids: list[str] = []

_COLLECTION_NAME = "anima_memories"


def _get_collection():
    global _embed_fn, _client, _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        _embed_fn = DefaultEmbeddingFunction()
    except Exception as e:
        print(f"⚠️ [Memory] ChromaDB unavailable ({e}) — memories disabled", flush=True)
        return None

    _client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    _collection = _client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=_embed_fn,
    )
    return _collection


def archive_conversation(user_text: str, companion_text: str, emotion: str = "neutral"):
    """Persist one conversation turn to vector memory."""
    col = _get_collection()
    if col is None:
        return
    name = config.get("companion_name", "Anima")
    try:
        col.add(
            documents=[f"User: {user_text}\n{name}: {companion_text}"],
            metadatas=[{
                "emotion":   emotion,
                "timestamp": datetime.datetime.now().isoformat(),
                "half_life": get_half_life(emotion),
            }],
            ids=[str(uuid.uuid4())],
        )
    except Exception as e:
        print(f"⚠️ [Memory/archive] {e}", flush=True)


def retrieve_relevant_memories(query: str, n_results: int = 3) -> str:
    """Return past conversation fragments most relevant to the query."""
    global _last_retrieved_ids
    _last_retrieved_ids = []

    col = _get_collection()
    if col is None:
        return ""

    try:
        fetch_n = min(n_results * 3, 24)
        results = col.query(
            query_texts=[query],
            n_results=fetch_n,
            include=["documents", "metadatas", "distances"],
        )

        docs  = results.get("documents",  [[]])[0]
        metas = results.get("metadatas",  [[]])[0]
        ids   = results.get("ids",        [[]])[0]
        dists = results.get("distances",  [[]])[0]

        if not docs:
            return ""

        scored = []
        for doc, meta, mem_id, dist in zip(docs, metas, ids, dists):
            similarity = max(0.0, 1.0 - dist / 2.0)
            score      = decay_score(similarity, meta.get("timestamp", ""), int(meta.get("half_life", 30)))
            scored.append((score, doc, mem_id))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]
        _last_retrieved_ids = [t[2] for t in top]

        return "[PAST CONTEXT]:\n" + "\n---\n".join(t[1] for t in top)

    except Exception as e:
        print(f"⚠️ [Memory/retrieve] {e}", flush=True)
        return ""


def reinforce_last_retrieved():
    """Reset timestamps on recently retrieved memories to slow their decay."""
    global _last_retrieved_ids
    if not _last_retrieved_ids:
        return
    col = _get_collection()
    if col is None:
        return
    try:
        now_iso  = datetime.datetime.now().isoformat()
        existing = col.get(ids=_last_retrieved_ids, include=["metadatas"])
        metas    = existing.get("metadatas", [])
        if metas:
            updated = [dict(m) | {"timestamp": now_iso} for m in metas]
            col.update(ids=_last_retrieved_ids, metadatas=updated)
    except Exception as e:
        print(f"⚠️ [Memory/reinforce] {e}", flush=True)
    finally:
        _last_retrieved_ids = []
