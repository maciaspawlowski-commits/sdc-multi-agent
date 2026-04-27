"""OTel + LLMetry setup for the SDC Multi-Agent System.

Signal flow:
  ┌────────────────────────────────────────────────────────────┐
  │  FastAPI HTTP spans       → OTel → Dash0                   │
  │  LangGraph node spans     → OTel → Dash0  (custom spans)   │
  │  ChatOllama LLM calls     → OTel → Dash0  (LLMetry/LC)     │
  │  Chroma vector queries    → OTel → Dash0  (manual + auto)  │
  │  Metrics (per-agent, etc) → OTel → Dash0                   │
  │  Log records              → OTel → Dash0                   │
  │                                                            │
  │  LangGraph node spans  ──────────────────→ LangSmith       │
  │  ChatOllama LLM calls  ──────────────────→ LangSmith       │
  │  (via LANGCHAIN_TRACING_V2 env var — zero extra code)      │
  └────────────────────────────────────────────────────────────┘

Chroma observability — two complementary layers:
  1. ChromaInstrumentor (auto) — patches the Chroma Python client and emits
     spans for every collection.query() call at the client-library level.
  2. Manual spans in vectorstore._query_collection() — adds domain-level
     attributes (sdc.agent, sdc.rag.collection_type, sdc.rag.min_distance,
     sdc.rag.results_after_filter) and records four custom metrics.

LangSmith and Dash0 are NOT mutually exclusive:
  • LangChain's callback system fires for LangSmith (graph topology, state diffs, replay)
  • OTel instrumentation fires for Dash0 (spans, metrics, logs, infra correlation)
  Both hooks run on every LLM/graph call with no conflict.
"""

import logging
import os

from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry import metrics, trace
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
