"""LangGraph node-level OTel instrumentation.

Adds one ``sdc.graph.node`` span per graph node invocation so the trace
waterfall in Dash0 mirrors the LangGraph execution tree visible in LangSmith:

  sdc.agent.session
    └── sdc.graph.node  [orchestrator]
          └── gen_ai.llm.call
    └── sdc.graph.node  [incident]
          └── gen_ai.llm.call          ← LLM decides to call tools
    └── sdc.graph.node  [incident_tools]
          ├── tool.invoke  [classify_priority]
          └── tool.invoke  [search_runbook_incident]
                └── chroma.query
    └── sdc.graph.node  [incident]
          └── gen_ai.llm.call          ← LLM synthesises tool results → answer

Context propagation note
------------------------
LangGraph runs sync node functions via asyncio's run_in_executor, which
copies the current contextvars snapshot to the worker thread (Python ≥ 3.7).
The ``start_as_current_span`` context manager therefore sees the active
``sdc.agent.session`` span as its parent, and everything called *inside* the
node (LLM callbacks, tool callbacks) sees the node span as the current span.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable

from opentelemetry import baggage, trace

from ..state import SDCState

logger = logging.getLogger(__name__)


# ── Agent node decorator ────────────────────────────────────────────────────

def graph_node_span(node_name: str, node_type: str = "agent") -> Callable:
    """Wrap a LangGraph node function in an ``sdc.graph.node`` OTel span.

    Usage::

        @graph_node_span("incident")
        def incident_node(state: SDCState) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: SDCState) -> dict:
            tracer = trace.get_tracer("sdc-agents")
            n_messages = len(state.get("messages", []))

            logger.info(
                "sdc.node.start node=%s type=%s ctx_messages=%d",
                node_name, node_type, n_messages,
            )

            session_id = baggage.get_baggage("session.id") or ""
            t0 = time.perf_counter()
            with tracer.start_as_current_span(
                "sdc.graph.node",
                attributes={
                    "sdc.node.name":           node_name,
                    "sdc.node.type":           node_type,
                    "sdc.messages.in_context": n_messages,
                    **({"session.id": session_id} if session_id else {}),
                },
            ):
                try:
                    result = func(state)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    out_messages = len(result.get("messages", []))
                    logger.info(
                        "sdc.node.exit node=%s type=%s latency_ms=%.1f out_messages=%d",
                        node_name, node_type, latency_ms, out_messages,
                    )
                    return result
                except Exception as exc:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    logger.error(
                        "sdc.node.error node=%s type=%s latency_ms=%.1f error=%s",
                        node_name, node_type, latency_ms, exc,
                    )
                    raise

        return wrapper
    return decorator


# ── Instrumented ToolNode ───────────────────────────────────────────────────

def make_instrumented_tool_node(tools: list, node_name: str) -> Callable:
    """Return a callable that wraps a LangGraph ``ToolNode`` in an OTel span.

    All ``tool.invoke`` spans emitted by ``SDCToolsCallback`` fire *inside*
    this span's context, so they appear as children in the trace tree.

    Usage in graph.py::

        g.add_node(
            "incident_tools",
            make_instrumented_tool_node(get_incident_tools(), "incident_tools"),
        )
    """
    from langgraph.prebuilt import ToolNode

    inner = ToolNode(tools)

    def wrapper(state: SDCState) -> dict:
        tracer = trace.get_tracer("sdc-agents")

        msgs = state.get("messages", [])
        pending = len(getattr(msgs[-1], "tool_calls", None) or []) if msgs else 0
        tool_names = (
            [tc.get("name", "?") for tc in (msgs[-1].tool_calls or [])]
            if msgs and hasattr(msgs[-1], "tool_calls") and msgs[-1].tool_calls
            else []
        )

        logger.info(
            "sdc.node.start node=%s type=tool_executor pending_calls=%d tools=%s",
            node_name, pending, ",".join(tool_names) or "none",
        )

        session_id = baggage.get_baggage("session.id") or ""
        t0 = time.perf_counter()
        with tracer.start_as_current_span(
            "sdc.graph.node",
            attributes={
                "sdc.node.name":          node_name,
                "sdc.node.type":          "tool_executor",
                "sdc.node.pending_calls": pending,
                **({"session.id": session_id} if session_id else {}),
            },
        ):
            try:
                result = inner.invoke(state)
                latency_ms = (time.perf_counter() - t0) * 1000
                logger.info(
                    "sdc.node.exit node=%s type=tool_executor latency_ms=%.1f calls_executed=%d",
                    node_name, latency_ms, pending,
                )
                return result
            except Exception as exc:
                latency_ms = (time.perf_counter() - t0) * 1000
                logger.error(
                    "sdc.node.error node=%s type=tool_executor latency_ms=%.1f error=%s",
                    node_name, latency_ms, exc,
                )
                raise

    return wrapper
