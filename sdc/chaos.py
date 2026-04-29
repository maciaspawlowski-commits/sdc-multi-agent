"""Chaos injection for the SDC Multi-Agent System.

Exposes a global ChaosState that other modules check at runtime.

Modes
-----
  none         — normal operation
  llm_slow     — add artificial delay to every LLM call (visible latency spike in Dash0)
  llm_error    — randomly fail LLM calls (configurable probability, default 50 %)
  tool_error   — randomly fail tool calls (configurable probability, default 50 %)
  rag_degraded — force empty RAG results (simulates stale / missing embeddings)

Every injected event emits a chaos.* OTel span + increments sdc.chaos.injections.total.
"""

import logging
import random
import time
from dataclasses import dataclass, field

from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry import metrics, trace
from opentelemetry.trace import StatusCode

logger = logging.getLogger(__name__)

VALID_MODES = {"none", "llm_slow", "llm_error", "tool_error", "rag_degraded"}

MODE_DESCRIPTIONS = {
    "none":         "Normal operation",
    "llm_slow":     "Artificial delay on every LLM call",
    "llm_error":    "Random LLM call failures",
    "tool_error":   "Random tool call failures",
    "rag_degraded": "Force empty RAG results (simulates missing embeddings)",
}


@dataclass
class _ChaosState:
    mode: str = "none"
    probability: float = 0.5   # used by llm_error / tool_error
    delay_ms: int = 3000        # used by llm_slow
    injections: int = 0         # total events fired since last reset


_state = _ChaosState()
_chaos_counter = None


def _get_counter():
    global _chaos_counter
    if _chaos_counter is None:
        meter = metrics.get_meter("sdc.chaos")
        _chaos_counter = meter.create_counter(
            "sdc.chaos.injections.total",
            description="Total chaos injections fired, labelled by mode",
            unit="{injections}",
        )
    return _chaos_counter


# ── Public API ────────────────────────────────────────────────────────────────

def get_state() -> dict:
    return {
        "mode":                   _state.mode,
        "description":            MODE_DESCRIPTIONS.get(_state.mode, ""),
        "probability":            _state.probability,
        "delay_ms":               _state.delay_ms,
        "injections_this_session": _state.injections,
        "active":                 _state.mode != "none",
        "valid_modes":            MODE_DESCRIPTIONS,
    }


def set_mode(mode: str, probability: float = 0.5, delay_ms: int = 3000) -> dict:
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown mode '{mode}'. Valid: {sorted(VALID_MODES)}")
    _state.mode = mode
    _state.probability = max(0.0, min(1.0, probability))
    _state.delay_ms    = max(0, delay_ms)
    _state.injections  = 0
    logger.warning(
        "🔥 Chaos ON  mode=%s prob=%.0f%% delay_ms=%d",
        mode, _state.probability * 100, _state.delay_ms,
    )
    return get_state()


def reset() -> dict:
    _state.mode       = "none"
    _state.injections = 0
    logger.info("✅ Chaos OFF — normal operation restored")
    return get_state()


def is_rag_degraded() -> bool:
    """Called by vectorstore._query_collection to force empty results."""
    return _state.mode == "rag_degraded"


# ── LangChain callback ────────────────────────────────────────────────────────

class ChaosCallback(BaseCallbackHandler):
    """LangChain callback that injects latency / errors into LLM and tool calls.

    Setting raise_error = True ensures injected exceptions propagate through
    LangGraph's ToolNode and agent nodes rather than being silently swallowed.
    """

    raise_error: bool = True   # re-raise so LangGraph sees the failure

    # ── LLM hooks ────────────────────────────────────────────────────────────

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs) -> None:
        mode = _state.mode

        if mode == "llm_slow":
            tracer = trace.get_tracer("sdc.chaos")
            with tracer.start_as_current_span(
                "chaos.llm_slow",
                attributes={"chaos.mode": "llm_slow", "chaos.delay_ms": _state.delay_ms},
            ):
                logger.warning("🔥 Chaos: slowing LLM call by %d ms", _state.delay_ms)
                _state.injections += 1
                _get_counter().add(1, {"chaos.mode": "llm_slow"})
                time.sleep(_state.delay_ms / 1000.0)

        elif mode == "llm_error" and random.random() < _state.probability:
            _state.injections += 1
            _get_counter().add(1, {"chaos.mode": "llm_error"})
            tracer = trace.get_tracer("sdc.chaos")
            with tracer.start_as_current_span(
                "chaos.llm_error",
                attributes={"chaos.mode": "llm_error", "chaos.probability": _state.probability},
            ) as span:
                err = RuntimeError("Chaos: injected LLM failure")
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                logger.error("🔥 Chaos: injecting LLM error (prob=%.0f%%)", _state.probability * 100)
            raise RuntimeError("Chaos: injected LLM failure")

    # ── Tool hooks ────────────────────────────────────────────────────────────

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        if _state.mode == "tool_error" and random.random() < _state.probability:
            tool_name = serialized.get("name", "unknown")
            _state.injections += 1
            _get_counter().add(1, {"chaos.mode": "tool_error", "tool.name": tool_name})
            tracer = trace.get_tracer("sdc.chaos")
            with tracer.start_as_current_span(
                "chaos.tool_error",
                attributes={
                    "chaos.mode":        "tool_error",
                    "tool.name":         tool_name,
                    "chaos.probability": _state.probability,
                },
            ) as span:
                err = RuntimeError(f"Chaos: injected failure for tool '{tool_name}'")
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                logger.error("🔥 Chaos: injecting tool error for '%s'", tool_name)
            raise RuntimeError(f"Chaos: injected failure for tool '{tool_name}'")
