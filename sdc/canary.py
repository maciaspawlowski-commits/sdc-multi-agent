"""SDC Synthetic Canary — one-shot probe run by a K8s CronJob every 5 minutes.

Fires a fixed test question at /api/chat, measures the round-trip latency,
and exports three OTel signals tagged service.name=sdc-canary (clearly
separated from real user traffic in Dash0):

  sdc.canary.latency_ms      histogram  — end-to-end HTTP response time
  sdc.canary.requests_total  counter    — labelled by status: ok | error | timeout
  sdc.canary.up              gauge      — 1.0 healthy / 0.0 unhealthy

One root span (sdc.canary.probe) is also emitted so each CronJob run
appears in Dash0's trace list with full timing and error details.

Usage:
    python -m sdc.canary
"""

import logging
import os
import sys
import time

import requests as _requests

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import StatusCode

try:
    from opentelemetry.sdk.metrics._internal.exemplar import TraceBasedExemplarFilter as _ExF
except ImportError:
    _ExF = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sdc.canary")

# ── Config from environment ───────────────────────────────────────────────────
SVC_URL       = os.getenv("SVC_URL",           "http://sdc-agents:8000")
TIMEOUT_SECS  = int(os.getenv("CANARY_TIMEOUT_SECS", "45"))
CANARY_Q      = os.getenv(
    "CANARY_QUESTION",
    "What is the SLA target and escalation path for a P1 incident?",
)
ENDPOINT      = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
AUTH_TOKEN    = os.getenv("DASH0_AUTH_TOKEN",  "")
SERVICE_NAME  = os.getenv("OTEL_SERVICE_NAME", "sdc-canary")
ENVIRONMENT   = os.getenv("ENVIRONMENT",       "k8s")


# ── OTel bootstrap ────────────────────────────────────────────────────────────

def _setup() -> tuple:
    resource = Resource.create({
        "service.name":           SERVICE_NAME,
        "service.version":        "1.0.0",
        "deployment.environment": ENVIRONMENT,
        "sdc.component":          "canary",
    })

    headers: dict = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    # Traces
    tp = TracerProvider(resource=resource)
    if ENDPOINT:
        tp.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{ENDPOINT}/v1/traces", headers=headers)
            )
        )
    else:
        tp.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(tp)

    # Metrics — short interval; we call shutdown() before exit to force final flush
    if ENDPOINT:
        m_exp = OTLPMetricExporter(endpoint=f"{ENDPOINT}/v1/metrics", headers=headers)
    else:
        m_exp = ConsoleMetricExporter()

    reader = PeriodicExportingMetricReader(m_exp, export_interval_millis=5_000)
    mp = MeterProvider(
        resource=resource,
        metric_readers=[reader],
        **({'exemplar_filter': _ExF()} if _ExF else {}),
    )
    metrics.set_meter_provider(mp)

    tracer = trace.get_tracer("sdc.canary")
    meter  = metrics.get_meter("sdc.canary")

    latency_hist = meter.create_histogram(
        "sdc.canary.latency_ms",
        description="End-to-end HTTP latency of the synthetic canary probe",
        unit="ms",
    )
    req_counter = meter.create_counter(
        "sdc.canary.requests_total",
        description="Total canary probe attempts, labelled by status (ok|error|timeout)",
        unit="{requests}",
    )
    up_gauge = meter.create_gauge(
        "sdc.canary.up",
        description="1.0 = last probe succeeded, 0.0 = last probe failed",
        unit="1",
    )

    return tracer, latency_hist, req_counter, up_gauge, tp, mp


# ── Probe logic ───────────────────────────────────────────────────────────────

def run() -> int:
    """Execute one canary probe. Returns 0 on success, 1 on failure."""
    tracer, lat_hist, req_ctr, up_gauge, tp, mp = _setup()

    url    = f"{SVC_URL}/api/chat"
    status = "ok"
    latency_ms = 0.0

    with tracer.start_as_current_span(
        "sdc.canary.probe",
        attributes={
            "canary.url":      url,
            "canary.question": CANARY_Q[:200],
            "canary.timeout":  TIMEOUT_SECS,
        },
    ) as span:
        t0 = time.perf_counter()
        try:
            resp = _requests.post(
                url,
                json={"message": CANARY_Q},
                timeout=TIMEOUT_SECS,
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            if resp.status_code == 200:
                data  = resp.json()
                agent = data.get("agent", "unknown")
                span.set_attribute("canary.status",       "ok")
                span.set_attribute("canary.http_status",  resp.status_code)
                span.set_attribute("canary.latency_ms",   round(latency_ms, 1))
                span.set_attribute("canary.agent",        agent)
                span.set_attribute("canary.response_len", len(data.get("response", "")))
                span.set_status(StatusCode.OK)
                logger.info(
                    "✅ Canary OK  agent=%s latency_ms=%.0f url=%s",
                    agent, latency_ms, url,
                )
            else:
                status = "error"
                span.set_attribute("canary.status",      "error")
                span.set_attribute("canary.http_status", resp.status_code)
                span.set_status(StatusCode.ERROR, f"HTTP {resp.status_code}")
                logger.error("❌ Canary HTTP error  status=%d url=%s", resp.status_code, url)

        except _requests.Timeout:
            latency_ms = (time.perf_counter() - t0) * 1000
            status = "timeout"
            span.set_attribute("canary.status",   "timeout")
            span.set_attribute("canary.latency_ms", round(latency_ms, 1))
            span.record_exception(TimeoutError(f"No response within {TIMEOUT_SECS}s"))
            span.set_status(StatusCode.ERROR, f"Timeout after {TIMEOUT_SECS}s")
            logger.error("⏱  Canary TIMEOUT after %ds url=%s", TIMEOUT_SECS, url)

        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            status = "error"
            span.set_attribute("canary.status",     "error")
            span.set_attribute("canary.latency_ms", round(latency_ms, 1))
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            logger.error("❌ Canary error: %s  url=%s", exc, url)

        # Emit metrics (recorded inside the active span → exemplars captured)
        attrs = {"canary.status": status}
        lat_hist.record(latency_ms, attrs)
        req_ctr.add(1, attrs)
        up_gauge.set(0.0 if status != "ok" else 1.0, {})

    # Shutdown flushes the BatchSpanProcessor and triggers a final metric export
    tp.shutdown()
    mp.shutdown()

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(run())
