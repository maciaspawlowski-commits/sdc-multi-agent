"""OpenTelemetry setup — exports traces, metrics, and logs to Dash0 (OTLP).

LLM calls are auto-instrumented via LLMetry (Traceloop's opentelemetry-instrumentation-openai).
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def setup_telemetry(app=None, service_name: str = None) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    auth_token = os.getenv("DASH0_AUTH_TOKEN", "")

    resource = Resource.create(
        {
            "service.name": service_name or os.getenv("OTEL_SERVICE_NAME", "llm-demo"),
            "service.version": "5.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "local"),
        }
    )

    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    if dataset := os.getenv("DASH0_DATASET", ""):
        headers["Dash0-Dataset"] = dataset

    # ── Traces ──────────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        span_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers)
        logger.info("Tracing → %s", endpoint)
    else:
        span_exporter = ConsoleSpanExporter()
        logger.info("Tracing → console")

    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ─────────────────────────────────────────────────────────────
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers)
        logger.info("Metrics → %s", endpoint)
    else:
        metric_exporter = ConsoleMetricExporter()
        logger.info("Metrics → console")

    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15_000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # ── Logs ────────────────────────────────────────────────────────────────
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        log_exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
        logger.info("Logs → %s", endpoint)
    else:
        log_exporter = ConsoleLogExporter()
        logger.info("Logs → console")

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(log_provider)

    # Bridge Python logging → OTel LogRecords (injects trace_id/span_id)
    LoggingInstrumentor().instrument(set_logging_format=True, log_level=logging.INFO)

    # ── LLMetry — auto-instrument OpenAI SDK calls ───────────────────────────
    OpenAIInstrumentor().instrument(capture_message_content=True)

    # ── Auto-instrument outbound httpx calls (propagates W3C trace context) ──
    HTTPXClientInstrumentor().instrument()

    # ── Auto-instrument FastAPI HTTP layer ───────────────────────────────────
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
