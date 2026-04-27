"""OTel + LLMetry setup for the SDC Multi-Agent System.

Signal flow:
  ┌────────────────────────────────────────────────────────────┐
  │  FastAPI HTTP spans       → OTel → Dash0                   │
  │  LangGraph node spans     → OTel → Dash0  (custom spans)   │
  │  ChatOllama LLM calls     → OTel → Dash0  (SDCOTelCallback)│
  │  Tool executions          → OTel → Dash0  (SDCToolsCallback)│
  │  Chroma vector queries    → OTel → Dash0  (manual + auto)  │
  │  Metrics (per-agent, etc) → OTel → Dash0                   │
  │  Log records              → OTel → Dash0                   │
  │                                                            │
  │  LangGraph node spans  ──────────────────→ LangSmith       │
  │  ChatOllama LLM calls  ──────────────────→ LangSmith       │
  │  Tool calls            ──────────────────→ LangSmith       │
  │  (via LANGCHAIN_TRACING_V2 env var — zero extra code)      │
  └────────────────────────────────────────────────────────────┘

Chroma observability — two complementary layers:
  1. ChromaInstrumentor (auto) — patches the Chroma Python client and emits
     spans for every collection.query() call at the client-library level.
  2. Manual spans in vectorstore._query_collection() — adds domain-level
     attributes (sdc.agent, sdc.rag.collection_type, sdc.rag.min_distance,
     sdc.rag.results_after_filter) and records four custom metrics.

Tool observability — SDCToolsCallback:
  Registered via graph ainvoke config so LangGraph's ToolNode passes it to
  every tool.invoke() call. Fires on_tool_start / on_tool_end / on_tool_error.
  Each tool execution produces:
    • A "tool.invoke" OTel span (child of the active sdc.agent.session span)
      with: tool.name, sdc.agent, tool.type (rag|domain), tool.input_preview,
            tool.output_length, tool.latency_ms
    • sdc.tool.calls.total counter  (by tool, agent, status, type)
    • sdc.tool.duration_ms histogram (by tool, agent, type)

LangSmith and Dash0 are NOT mutually exclusive:
  • LangChain's callback system fires for LangSmith (graph topology, state diffs, replay)
  • OTel instrumentation fires for Dash0 (spans, metrics, logs, infra correlation)
  Both hooks run on every LLM/graph call with no conflict.
"""

import logging
import os

from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry import metrics, trace
from opentelemetry.trace import SpanKind, StatusCode
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def setup_sdc_telemetry(app=None, service_version: str = "1.0.0") -> None:
    """Configure OTel providers and attach all instrumentors for the SDC app."""

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    auth_token = os.getenv("DASH0_AUTH_TOKEN", "")

    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "sdc-agents"),
        "service.version": service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "local"),
        "llm.framework": "langgraph",
        "llm.runtime": "ollama",
    })

    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    if dataset := os.getenv("DASH0_DATASET", ""):
        headers["Dash0-Dataset"] = dataset

    # ── Traces ───────────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        span_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers)
        logger.info("Traces  → Dash0 %s", endpoint)
    else:
        span_exporter = ConsoleSpanExporter()
        logger.info("Traces  → console (set OTEL_EXPORTER_OTLP_ENDPOINT to send to Dash0)")

    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ──────────────────────────────────────────────────────────────
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers)
        logger.info("Metrics → Dash0 %s", endpoint)
    else:
        metric_exporter = ConsoleMetricExporter()
        logger.info("Metrics → console")

    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15_000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # ── Logs ─────────────────────────────────────────────────────────────────
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        log_exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
        logger.info("Logs    → Dash0 %s", endpoint)
    else:
        log_exporter = ConsoleLogExporter()
        logger.info("Logs    → console")

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(log_provider)

    # Bridge Python logging → OTel LogRecords (injects trace_id/span_id automatically)
    LoggingInstrumentor().instrument(set_logging_format=True, log_level=logging.INFO)

    # ── LLMetry: LangChain / LangGraph LLM calls → OTel spans ────────────────
    # opentelemetry-instrumentation-langchain has an API mismatch with
    # opentelemetry-instrumentation>=0.62b0, so we use a custom callback
    # handler (SDCOTelCallback) that creates equivalent GenAI-semantic spans.
    # Registered per-agent call in sdc/agents/base_llm.py.
    logger.info("LLMetry → using SDCOTelCallback for LangChain spans")

    # ── Chroma auto-instrumentation ───────────────────────────────────────────
    # Patches chromadb.Collection.query / add / delete at the client level.
    # Complements the manual spans in vectorstore._query_collection().
    try:
        from opentelemetry.instrumentation.chromadb import ChromaInstrumentor
        ChromaInstrumentor().instrument()
        logger.info("Chroma  → auto-instrumented (ChromaInstrumentor)")
    except Exception as exc:
        logger.warning("Chroma auto-instrumentation unavailable: %s", exc)

    # ── FastAPI HTTP layer ────────────────────────────────────────────────────
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI → instrumented")

    _log_langsmith_status()


class SDCOTelCallback(BaseCallbackHandler):
    """LangChain callback handler that creates OTel spans for every LLM call.

    Replaces the broken opentelemetry-instrumentation-langchain package.
    Each ChatOllama.invoke() produces a child span under the active
    sdc.agent.session span with GenAI semantic convention attributes.
    """

    def __init__(self, agent_key: str):
        self._agent_key = agent_key
        self._spans: dict = {}

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs) -> None:
        import os
        model = os.getenv("LLM_MODEL", "llama3.2")
        tracer = trace.get_tracer("sdc-agents")
        span = tracer.start_span(
            "gen_ai.llm.call",
            attributes={
                "gen_ai.system": "ollama",
                "gen_ai.request.model": model,
                "sdc.agent": self._agent_key,
                "gen_ai.prompt": str(prompts[0])[:2000] if prompts else "",
            },
        )
        run_id = kwargs.get("run_id")
        if run_id:
            self._spans[str(run_id)] = span

    def on_llm_end(self, response, **kwargs) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._spans.pop(run_id, None)
        if span is None:
            return
        try:
            gen = response.generations[0][0] if response.generations else None
            if gen:
                span.set_attribute("gen_ai.completion", str(gen.text)[:2000])
            if hasattr(response, "llm_output") and response.llm_output:
                usage = response.llm_output.get("usage", {})
                if usage:
                    span.set_attribute("gen_ai.usage.prompt_tokens", usage.get("prompt_tokens", 0))
                    span.set_attribute("gen_ai.usage.completion_tokens", usage.get("completion_tokens", 0))
        finally:
            span.end()

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._spans.pop(run_id, None)
        if span:
            span.record_exception(error)
            span.end()



# ---------------------------------------------------------------------------
# Tool name → agent key mapping (used by SDCToolsCallback)
# ---------------------------------------------------------------------------

_RAG_TOOL_PREFIXES = ("search_runbook_", "search_historical_records_")

_DOMAIN_TOOL_AGENT: dict[str, str] = {
    # Incident
    "classify_priority":             "incident",
    "calculate_resolution_deadline": "incident",
    "get_escalation_path":           "incident",
    # Change
    "check_freeze_window":           "change",
    "classify_change_type":          "change",
    "next_cab_meeting":              "change",
    # Problem
    "check_problem_trigger":         "problem",
    "suggest_rca_method":            "problem",
    "format_kedb_entry":             "problem",
    # Service
    "get_request_sla":               "service",
    "validate_request_fields":       "service",
    "check_approval_chain":          "service",
    # SLA
    "calculate_availability":        "sla",
    "calculate_sla_credit":          "sla",
    "sla_breach_warning":            "sla",
}


def _tool_meta(tool_name: str) -> tuple[str, str]:
    """Return (agent_key, tool_type) for a given tool name.

    tool_type is either 'rag' (search tools) or 'domain' (calculation/lookup tools).
    """
    for prefix in _RAG_TOOL_PREFIXES:
        if tool_name.startswith(prefix):
            agent = tool_name[len(prefix):]          # e.g. "incident"
            return agent, "rag"

    agent = _DOMAIN_TOOL_AGENT.get(tool_name, "unknown")
    return agent, "domain"


# ---------------------------------------------------------------------------
# SDCToolsCallback — OTel instrumentation for tool executions
# ---------------------------------------------------------------------------

class SDCToolsCallback(BaseCallbackHandler):
    """LangChain callback handler that creates OTel spans for every tool call.

    Register this via the graph's ainvoke config so LangGraph's ToolNode
    propagates it to every tool.invoke() call:

        await sdc_graph.ainvoke(state, config={"callbacks": [SDCToolsCallback()]})

    Span hierarchy:
        sdc.agent.session          (FastAPI handler)
          └── gen_ai.llm.call      (SDCOTelCallback — LLM reasoning step)
          └── tool.invoke          (SDCToolsCallback — this class)
                └── chroma.query   (vectorstore — only for RAG tools)

    Metrics emitted (sdc.tools meter):
        sdc.tool.calls.total    — counter  (tool_name, agent, tool_type, status)
        sdc.tool.duration_ms    — histogram (tool_name, agent, tool_type)
    """

    def __init__(self) -> None:
        self._spans: dict[str, object] = {}
        self._start_times: dict[str, float] = {}
        self._tool_calls_counter: object = None
        self._tool_duration_hist: object = None

    def _ensure_metrics(self) -> None:
        if self._tool_calls_counter is None:
            meter = metrics.get_meter("sdc.tools")
            self._tool_calls_counter = meter.create_counter(
                name="sdc.tool.calls.total",
                description="Total number of agent tool calls",
                unit="{calls}",
            )
            self._tool_duration_hist = meter.create_histogram(
                name="sdc.tool.duration_ms",
                description="Tool execution latency in milliseconds",
                unit="ms",
            )

    def on_tool_start(
        self, serialized: dict, input_str: str, **kwargs
    ) -> None:
        import time as _time
        from opentelemetry import context as ctx_api

        tool_name = serialized.get("name", "unknown_tool")
        agent_key, tool_type = _tool_meta(tool_name)

        tracer = trace.get_tracer("sdc.tools")
        # Capture the current OTel context so the span is a child of
        # whatever is active (sdc.agent.session) at invocation time.
        span = tracer.start_span(
            "tool.invoke",
            context=ctx_api.get_current(),
            attributes={
                "tool.name":       tool_name,
                "sdc.agent":       agent_key,
                "tool.type":       tool_type,           # "rag" | "domain"
                "tool.input_preview": str(input_str)[:300],
            },
        )

        run_id = str(kwargs.get("run_id", ""))
        self._spans[run_id] = span
        self._start_times[run_id] = _time.perf_counter()

        logger.debug(
            "tool.start [%s/%s] input_len=%d",
            agent_key, tool_name, len(str(input_str)),
        )

    def on_tool_end(self, output: str, **kwargs) -> None:
        import time as _time

        run_id = str(kwargs.get("run_id", ""))
        span = self._spans.pop(run_id, None)
        t0 = self._start_times.pop(run_id, None)

        if span is None:
            return

        latency_ms = (_time.perf_counter() - t0) * 1000 if t0 else 0.0
        output_str = str(output) if output is not None else ""
        tool_name = span.name  # "tool.invoke" — get attrs from span
        # Re-read attrs from span for metric labels
        attrs = dict(span.attributes or {})
        agent_key  = attrs.get("sdc.agent",  "unknown")
        tool_type  = attrs.get("tool.type",  "domain")
        tool_name  = attrs.get("tool.name",  "unknown")

        span.set_attribute("tool.output_length", len(output_str))
        span.set_attribute("tool.output_preview", output_str[:500])
        span.set_attribute("tool.latency_ms", round(latency_ms, 2))
        span.set_status(StatusCode.OK)
        span.end()

        self._ensure_metrics()
        metric_attrs = {
            "tool.name":  tool_name,
            "sdc.agent":  agent_key,
            "tool.type":  tool_type,
            "status":     "ok",
        }
        self._tool_calls_counter.add(1, metric_attrs)
        self._tool_duration_hist.record(latency_ms, metric_attrs)

        logger.debug(
            "tool.end [%s/%s] latency=%.1fms output_len=%d",
            agent_key, tool_name, latency_ms, len(output_str),
        )

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        import time as _time

        run_id = str(kwargs.get("run_id", ""))
        span = self._spans.pop(run_id, None)
        t0 = self._start_times.pop(run_id, None)

        if span is None:
            return

        latency_ms = (_time.perf_counter() - t0) * 1000 if t0 else 0.0
        attrs = dict(span.attributes or {})
        agent_key = attrs.get("sdc.agent", "unknown")
        tool_type = attrs.get("tool.type", "domain")
        tool_name = attrs.get("tool.name", "unknown")

        span.record_exception(error)
        span.set_attribute("tool.latency_ms", round(latency_ms, 2))
        span.set_status(StatusCode.ERROR, str(error))
        span.end()

        self._ensure_metrics()
        metric_attrs = {
            "tool.name":  tool_name,
            "sdc.agent":  agent_key,
            "tool.type":  tool_type,
            "status":     "error",
        }
        self._tool_calls_counter.add(1, metric_attrs)
        self._tool_duration_hist.record(latency_ms, metric_attrs)

        logger.warning(
            "tool.error [%s/%s] latency=%.1fms error=%s",
            agent_key, tool_name, latency_ms, error,
        )


def _log_langsmith_status() -> None:
    """Log whether LangSmith tracing is active (controlled purely by env vars)."""
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        project = os.getenv("LANGCHAIN_PROJECT", "(default)")
        has_key = bool(os.getenv("LANGCHAIN_API_KEY", ""))
        if has_key:
            logger.info("LangSmith → tracing enabled, project: %s", project)
        else:
            logger.warning(
                "LangSmith → LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY not set — "
                "traces will be dropped. Get a key at https://smith.langchain.com"
            )
    else:
        logger.info(
            "LangSmith → disabled (set LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY to enable)"
        )
