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

from functools import wraps
from typing import Callable

from opentelemetry import trace

from ..state import SDCState


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
            with tracer.start_as_current_span(
                "sdc.graph.node",
                attributes={
                    "sdc.node.name":         node_name,
                    "sdc.node.type":         node_type,
                    "sdc.messages.in_context": n_messages,
                },
            ):
                return func(state)
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

        # Count the tool calls that are about to execute
        msgs = state.get("messages", [])
        pending = 0
        if msgs:
            pending = len(getattr(msgs[-1], "tool_calls", None) or [])

        with tracer.start_as_current_span(
            "sdc.graph.node",
            attributes={
                "sdc.node.name":          node_name,
                "sdc.node.type":          "tool_executor",
                "sdc.node.pending_calls": pending,
            },
        ):
            return inner.invoke(state)

    return wrapper
