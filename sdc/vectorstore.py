"""Chroma vector store for SDC runbook knowledge and historical operational records.

Two collections per agent:
  - sdc_runbook_{key}  — procedural runbook chunks (how-to guidance)
  - sdc_records_{key}  — historical operational records (past incidents, changes, etc.)

Both are queried at inference time and combined into the agent's context.

Usage:
    from sdc.vectorstore import retrieve, retrieve_records, retrieve_both
    context = retrieve_both("incident", "connection pool exhaustion P1")
"""

import logging
import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

logger = logging.getLogger(__name__)

AGENT_KEYS = ("incident", "change", "problem", "service", "sla")

# Persist embeddings alongside the project
_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")

# Module-level client — one connection, reused across all requests
_client: Optional[chromadb.PersistentClient] = None
_embed_fn = DefaultEmbeddingFunction()

_COSINE_THRESHOLD = 0.7  # distance > this → low relevance, filtered out


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=_DB_PATH)
        logger.info("Chroma client initialised — db: %s", _DB_PATH)
    return _client


# ---------------------------------------------------------------------------
# Collection name helpers
# ---------------------------------------------------------------------------

def runbook_collection_name(agent_key: str) -> str:
    return f"sdc_runbook_{agent_key}"


def records_collection_name(agent_key: str) -> str:
    return f"sdc_records_{agent_key}"


# Keep original name for backward compat
def collection_name(agent_key: str) -> str:
    return runbook_collection_name(agent_key)


# ---------------------------------------------------------------------------
# Collection accessors
# ---------------------------------------------------------------------------

def get_collection(agent_key: str) -> chromadb.Collection:
    """Return (or create) the runbook collection for the given agent."""
    return _get_client().get_or_create_collection(
        name=runbook_collection_name(agent_key),
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def get_records_collection(agent_key: str) -> chromadb.Collection:
    """Return (or create) the historical records collection for the given agent."""
    return _get_client().get_or_create_collection(
        name=records_collection_name(agent_key),
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Core retrieval helper
# ---------------------------------------------------------------------------

def _query_collection(col: chromadb.Collection, query: str, k: int) -> str:
    """Query a collection and return filtered, joined document strings."""
    if col.count() == 0:
        return ""

    results = col.query(
        query_texts=[query],
        n_results=min(k, col.count()),
        include=["documents", "distances"],
    )
    docs = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    relevant = [doc for doc, dist in zip(docs, distances) if dist < _COSINE_THRESHOLD]
    return "\n\n---\n\n".join(relevant)


# ---------------------------------------------------------------------------
# Public retrieval functions
# ---------------------------------------------------------------------------

def retrieve(agent_key: str, query: str, k: int = 4) -> str:
    """Return top-k relevant runbook chunks as a single context string."""
    try:
        col = get_collection(agent_key)
        return _query_collection(col, query, k)
    except Exception as exc:
        logger.warning("Runbook retrieval failed for '%s': %s", agent_key, exc)
        return ""


def retrieve_records(agent_key: str, query: str, k: int = 4) -> str:
    """Return top-k relevant historical records as a single context string."""
    try:
        col = get_records_collection(agent_key)
        return _query_collection(col, query, k)
    except Exception as exc:
        logger.warning("Records retrieval failed for '%s': %s", agent_key, exc)
        return ""


def retrieve_both(agent_key: str, query: str, k: int = 3) -> tuple[str, str]:
    """Return (runbook_context, records_context) for a query.

    Each section uses k results (default 3 each, to keep total context manageable).
    """
    runbook_ctx = retrieve(agent_key, query, k=k)
    records_ctx = retrieve_records(agent_key, query, k=k)
    return runbook_ctx, records_ctx


# ---------------------------------------------------------------------------
# Health / stats
# ---------------------------------------------------------------------------

def collection_stats() -> dict:
    """Return document counts per collection — useful for health checks."""
    client = _get_client()
    stats: dict[str, dict] = {}
    for key in AGENT_KEYS:
        key_stats: dict[str, int] = {}
        for col_type, name_fn in (
            ("runbooks", runbook_collection_name),
            ("records", records_collection_name),
        ):
            try:
                col = client.get_collection(
                    name=name_fn(key),
                    embedding_function=_embed_fn,
                )
                key_stats[col_type] = col.count()
            except Exception:
                key_stats[col_type] = 0
        stats[key] = key_stats
    return stats
