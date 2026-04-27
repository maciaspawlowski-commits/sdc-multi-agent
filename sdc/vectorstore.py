"""Chroma vector store for SDC runbook knowledge and historical operational records.

Two collections per agent:
  - sdc_runbook_{key}  — procedural runbook chunks (how-to guidance)
  - sdc_records_{key}  — historical operational records (past incidents, changes, etc.)

Both are queried at inference time and combined into the agent's context.

Observability
-------------
Every call to _query_collection() produces:
  • An OTel span   — "chroma.query" with db.* and sdc.rag.* attributes
  • Histogram      — sdc.rag.query.duration_ms  (latency by agent + collection_type)
  • Histogram      — sdc.rag.results.count       (results passing relevance filter)
  • Histogram      — sdc.rag.min_distance        (quality of best embedding match)
  • Counter        — sdc.rag.empty_results.total (queries that returned nothing useful)

Spans are child spans of whatever is active (i.e. the sdc.agent.session span),
so every RAG call appears nested inside the correct agent trace in Dash0.

Usage:
    from sdc.vectorstore import retrieve, retrieve_records, retrieve_both
    context = retrieve_both("incident", "connection pool exhaustion P1")
"""

import logging
import time
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from opentelemetry import metrics, trace
from opentelemetry.trace import SpanKind, StatusCode

logger = logging.getLogger(__name__)

AGENT_KEYS = ("incident", "change", "problem", "service", "sla")

_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")

_client: Optional[chromadb.PersistentClient] = None
_embed_fn = DefaultEmbeddingFunction()

_COSINE_THRESHOLD = 0.7  # distance > this → low relevance, filtered out

# ---------------------------------------------------------------------------
# OTel instruments — obtained lazily so they work after provider initialisation
# ---------------------------------------------------------------------------

_tracer: Optional[trace.Tracer] = None
_query_latency: Optional[metrics.Histogram] = None
_result_count: Optional[metrics.Histogram] = None
_min_distance: Optional[metrics.Histogram] = None
_empty_results: Optional[metrics.Counter] = None


def _instruments():
    """Initialise OTel instruments on first use (providers are set up by then)."""
    global _tracer, _query_latency, _result_count, _min_distance, _empty_results
    if _tracer is None:
        _tracer = trace.get_tracer("sdc.vectorstore")

        meter = metrics.get_meter("sdc.vectorstore")

        _query_latency = meter.create_histogram(
            name="sdc.rag.query.duration_ms",
            description="Chroma vector query latency in milliseconds",
            unit="ms",
        )
        _result_count = meter.create_histogram(
            name="sdc.rag.results.count",
            description="Number of chunks returned after relevance filtering",
            unit="{chunks}",
        )
        _min_distance = meter.create_histogram(
            name="sdc.rag.min_distance",
            description="Cosine distance of the closest matching chunk (lower = more relevant)",
            unit="1",
        )
        _empty_results = meter.create_counter(
            name="sdc.rag.empty_results.total",
            description="Number of queries that returned zero relevant chunks",
            unit="{queries}",
        )

    return _tracer, _query_latency, _result_count, _min_distance, _empty_results


# ---------------------------------------------------------------------------
# Chroma client
# ---------------------------------------------------------------------------

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


def collection_name(agent_key: str) -> str:
    """Backward-compat alias for runbook collection name."""
    return runbook_collection_name(agent_key)


# ---------------------------------------------------------------------------
# Collection accessors
# ---------------------------------------------------------------------------

def get_collection(agent_key: str) -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=runbook_collection_name(agent_key),
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def get_records_collection(agent_key: str) -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=records_collection_name(agent_key),
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Core retrieval — single instrumented chokepoint
# ---------------------------------------------------------------------------

def _query_collection(
    col: chromadb.Collection,
    query: str,
    k: int,
    agent_key: str,
    collection_type: str,  # "runbooks" | "records"
) -> str:
    """Query a Chroma collection and return filtered, joined document strings.

    Every call is wrapped in an OTel span (child of the active agent session
    span) and records latency, result count, and relevance quality metrics.
    """
    if col.count() == 0:
        logger.debug(
            "Chroma collection '%s' is empty — skipping RAG retrieval", col.name
        )
        return ""

    tracer, lat_hist, res_hist, dist_hist, empty_ctr = _instruments()

    metric_attrs = {"sdc.agent": agent_key, "sdc.rag.collection_type": collection_type}

    with tracer.start_as_current_span(
        "chroma.query",
        kind=SpanKind.CLIENT,
        attributes={
            # DB semantic conventions
            "db.system": "chromadb",
            "db.collection.name": col.name,
            # SDC / RAG domain attributes
            "sdc.agent": agent_key,
            "sdc.rag.collection_type": collection_type,
            "sdc.rag.query_top_k": k,
            "sdc.rag.query_preview": query[:200],
            "sdc.rag.collection_size": col.count(),
        },
    ) as span:
        t0 = time.perf_counter()
        try:
            results = col.query(
                query_texts=[query],
                n_results=min(k, col.count()),
                include=["documents", "distances"],
            )
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            logger.warning(
                "Chroma query failed [%s / %s]: %s", agent_key, collection_type, exc
            )
            raise

        latency_ms = (time.perf_counter() - t0) * 1000

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        relevant = [
            doc for doc, dist in zip(docs, distances) if dist < _COSINE_THRESHOLD
        ]

        # Best (minimum) distance across all raw candidates
        best_dist = min(distances) if distances else 1.0

        # Annotate span with result quality
        span.set_attribute("sdc.rag.candidates_returned", len(docs))
        span.set_attribute("sdc.rag.results_after_filter", len(relevant))
        span.set_attribute("sdc.rag.min_distance", round(best_dist, 4))
        span.set_attribute("sdc.rag.latency_ms", round(latency_ms, 2))
        span.set_attribute("sdc.rag.result_empty", len(relevant) == 0)
        span.set_status(StatusCode.OK)

        # Metrics
        lat_hist.record(latency_ms, metric_attrs)
        res_hist.record(len(relevant), metric_attrs)
        dist_hist.record(best_dist, metric_attrs)
        if not relevant:
            empty_ctr.add(1, metric_attrs)

        logger.debug(
            "chroma.query [%s/%s] latency=%.1fms candidates=%d relevant=%d best_dist=%.3f",
            agent_key, collection_type, latency_ms, len(docs), len(relevant), best_dist,
        )

        return "\n\n---\n\n".join(relevant)


# ---------------------------------------------------------------------------
# Public retrieval functions
# ---------------------------------------------------------------------------

def retrieve(agent_key: str, query: str, k: int = 4) -> str:
    """Return top-k relevant runbook chunks as a single context string."""
    try:
        col = get_collection(agent_key)
        return _query_collection(col, query, k, agent_key, "runbooks")
    except Exception as exc:
        logger.warning("Runbook retrieval failed for '%s': %s", agent_key, exc)
        return ""


def retrieve_records(agent_key: str, query: str, k: int = 4) -> str:
    """Return top-k relevant historical records as a single context string."""
    try:
        col = get_records_collection(agent_key)
        return _query_collection(col, query, k, agent_key, "records")
    except Exception as exc:
        logger.warning("Records retrieval failed for '%s': %s", agent_key, exc)
        return ""


def retrieve_both(agent_key: str, query: str, k: int = 3) -> tuple[str, str]:
    """Return (runbook_context, records_context) for a query.

    Each collection uses k results (default 3) — total max context: 6 chunks.
    """
    runbook_ctx = retrieve(agent_key, query, k=k)
    records_ctx = retrieve_records(agent_key, query, k=k)
    return runbook_ctx, records_ctx


# ---------------------------------------------------------------------------
# Health / stats
# ---------------------------------------------------------------------------

def collection_stats() -> dict:
    """Return document counts per collection — used by /health endpoint."""
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
