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
from opentelemetry import baggage, metrics, trace
from opentelemetry.trace import SpanKind, StatusCode
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
try:
    from opentelemetry.sdk.metrics._internal.exemplar import TraceBasedExemplarFilter as _ExemplarFilter
except ImportError:  # SDK < 1.27 fallback
    _ExemplarFilter = None
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def setup_sdc_telemetry(app=None, service_version: str = "7.2.0") -> None:
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
    # TraceBasedExemplarFilter: histogram buckets recorded inside an active span
    # automatically carry the span's trace_id + span_id — one click in Dash0
    # jumps from a latency spike on the chart directly to the trace that caused it.
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[reader],
        **({'exemplar_filter': _ExemplarFilter()} if _ExemplarFilter else {}),
    )
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
        self._t0: dict = {}
        # GenAI semantic convention metrics (OTel spec names)
        self._operation_duration_hist: object = None   # gen_ai.client.operation.duration
        self._token_usage_hist: object = None           # gen_ai.client.token.usage
        self._requests_counter: object = None           # gen_ai.client.requests.total (custom)

    def _ensure_llm_metrics(self) -> None:
        if self._operation_duration_hist is None:
            meter = metrics.get_meter("gen_ai")
            # Standard OTel GenAI semantic convention metrics
            # https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
            self._operation_duration_hist = meter.create_histogram(
                name="gen_ai.client.operation.duration",
                description="Duration of GenAI operation from the client's perspective",
                unit="s",  # seconds — per OTel GenAI spec
            )
            self._token_usage_hist = meter.create_histogram(
                name="gen_ai.client.token.usage",
                description="Measures number of input and output tokens used",
                unit="{token}",
            )
            self._requests_counter = meter.create_counter(
                name="gen_ai.client.requests.total",
                description="Total number of GenAI client requests by agent and status",
                unit="{request}",
            )

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs) -> None:
        import os, time as _time
        model = os.getenv("LLM_MODEL", "llama3.2")
        prompt_preview = str(prompts[0])[:200].replace("\n", " ") if prompts else ""
        logger.info(
            "sdc.llm.start agent=%s model=%s prompts=%d preview=%.200s",
            self._agent_key, model, len(prompts), prompt_preview,
        )
        session_id = baggage.get_baggage("session.id") or ""
        tracer = trace.get_tracer("sdc-agents")
        span = tracer.start_span(
            "gen_ai.llm.call",
            attributes={
                "gen_ai.system":        "ollama",
                "gen_ai.request.model": model,
                "sdc.agent":            self._agent_key,
                "gen_ai.prompt":        str(prompts[0])[:2000] if prompts else "",
                **({"session.id": session_id} if session_id else {}),
            },
        )
        run_id = kwargs.get("run_id")
        if run_id:
            self._spans[str(run_id)] = span
            self._t0[str(run_id)] = _time.perf_counter()

    def on_llm_end(self, response, **kwargs) -> None:
        import os, time as _time
        from opentelemetry import context as ctx_api

        run_id = str(kwargs.get("run_id", ""))
        span = self._spans.pop(run_id, None)
        t0   = self._t0.pop(run_id, None)
        if span is None:
            return

        latency_s  = (_time.perf_counter() - t0) if t0 else 0.0
        latency_ms = latency_s * 1000

        try:
            gen = response.generations[0][0] if response.generations else None
            completion_preview = ""
            prompt_tokens = completion_tokens = 0
            if gen:
                span.set_attribute("gen_ai.completion", str(gen.text)[:2000])
                completion_preview = str(gen.text)[:200].replace("\n", " ")
            prompts_raw = kwargs.get("prompts", [])
            prompt_text = str(prompts_raw[0]) if prompts_raw else (str(response.generations[0][0].message) if response.generations else "")
            if hasattr(response, "llm_output") and response.llm_output:
                usage = response.llm_output.get("usage", {})
                if usage:
                    prompt_tokens     = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
            # Ollama often returns 0 — fall back to char-length / 4 (rough tiktoken estimate)
            if not prompt_tokens:
                prompt_tokens = max(1, len(prompt_text) // 4)
            if not completion_tokens and gen:
                completion_tokens = max(1, len(str(gen.text)) // 4)
            span.set_attribute("gen_ai.usage.input_tokens",  prompt_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", completion_tokens)
            span.set_attribute("gen_ai.client.operation.duration", round(latency_s, 3))
            # Detect tool calls in the raw message if available
            tool_calls = 0
            if gen and hasattr(gen, "message") and hasattr(gen.message, "tool_calls"):
                tool_calls = len(gen.message.tool_calls or [])
            model = os.getenv("LLM_MODEL", "llama3.2")
            logger.info(
                "sdc.llm.end agent=%s model=%s tokens_in=%d tokens_out=%d "
                "tool_calls=%d latency_ms=%.0f preview=%.200s",
                self._agent_key, model, prompt_tokens, completion_tokens,
                tool_calls, latency_ms, completion_preview,
            )

            # ── GenAI metrics (OTel semantic conventions) ─────────────────────
            # Attach the gen_ai.llm.call span as the active context so the
            # TraceBasedExemplarFilter links each histogram bucket to this exact
            # LLM call span — one click from a latency spike → the full trace.
            self._ensure_llm_metrics()
            base_attrs = {
                "gen_ai.system":         "ollama",
                "gen_ai.request.model":  model,
                "gen_ai.operation.name": "chat",
                "sdc.agent":             self._agent_key,
            }
            ctx_token = ctx_api.attach(trace.set_span_in_context(span))
            try:
                # gen_ai.client.operation.duration — standard duration histogram (seconds)
                self._operation_duration_hist.record(latency_s, base_attrs)

                # gen_ai.client.token.usage — input + output tokens as separate data points
                # (uses Ollama's reported counts when available, char/4 estimate otherwise)
                self._token_usage_hist.record(
                    prompt_tokens,
                    {**base_attrs, "gen_ai.token.type": "input"},
                )
                self._token_usage_hist.record(
                    completion_tokens,
                    {**base_attrs, "gen_ai.token.type": "output"},
                )

                # gen_ai.client.requests.total — count by agent + status
                self._requests_counter.add(1, {**base_attrs, "status": "ok"})
            finally:
                ctx_api.detach(ctx_token)
        finally:
            span.end()

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._spans.pop(run_id, None)
        t0 = self._t0.pop(run_id, None)
        import os, time as _time
        latency_s = (_time.perf_counter() - t0) if t0 else 0.0
        model = os.getenv("LLM_MODEL", "llama3.2")
        logger.error(
            "sdc.llm.error agent=%s model=%s latency_ms=%.0f error=%s",
            self._agent_key, model, latency_s * 1000, error,
        )
        if span:
            span.record_exception(error)
            span.end()
        self._ensure_llm_metrics()
        self._requests_counter.add(1, {
            "gen_ai.system":         "ollama",
            "gen_ai.request.model":  model,
            "gen_ai.operation.name": "chat",
            "sdc.agent":             self._agent_key,
            "status":                "error",
        })



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

        session_id = baggage.get_baggage("session.id") or ""
        tracer = trace.get_tracer("sdc.tools")
        # Capture the current OTel context so the span is a child of
        # whatever is active (sdc.agent.session) at invocation time.
        span = tracer.start_span(
            "tool.invoke",
            context=ctx_api.get_current(),
            attributes={
                "tool.name":          tool_name,
                "sdc.agent":          agent_key,
                "tool.type":          tool_type,           # "rag" | "domain"
                "tool.input_preview": str(input_str)[:300],
                **({"session.id": session_id} if session_id else {}),
            },
        )

        run_id = str(kwargs.get("run_id", ""))
        self._spans[run_id] = span
        self._start_times[run_id] = _time.perf_counter()

        logger.info(
            "sdc.tool.start tool=%s agent=%s type=%s input_len=%d input=%.150s",
            tool_name, agent_key, tool_type, len(str(input_str)),
            str(input_str)[:150].replace("\n", " "),
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

        logger.info(
            "sdc.tool.end tool=%s agent=%s type=%s latency_ms=%.1f output_len=%d output=%.150s",
            tool_name, agent_key, tool_type, latency_ms, len(output_str),
            output_str[:150].replace("\n", " "),
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
            "sdc.tool.error tool=%s agent=%s type=%s latency_ms=%.1f error=%s",
            tool_name, agent_key, tool_type, latency_ms, error,
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
