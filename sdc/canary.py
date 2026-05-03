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
ENDPOINT      = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
AUTH_TOKEN    = os.getenv("DASH0_AUTH_TOKEN",  "")
SERVICE_NAME  = os.getenv("OTEL_SERVICE_NAME", "sdc-canary")
ENVIRONMENT   = os.getenv("ENVIRONMENT",       "k8s")

# ── Canary rotation ──────────────────────────────────────────────────────────
# One curated prompt per specialist.  The probe rotates through these so the
# orchestrator's routing logic is exercised across all five agents within
# every full cycle (50 min at the default 10-min CronJob cadence).
#
# These match the suggestion chips in the Operator Console (static/console/
# data.js → window.SUGGESTIONS) so the canary signal is comparable to what
# real operators would send.
#
# To force a single fixed prompt (e.g. for debugging), set CANARY_QUESTION
# in the environment — it short-circuits the rotation.
CANARY_QUESTIONS: list[tuple[str, str]] = [
    ("incident",
     "Our payment gateway is completely down and approximately 450,000 customers are "
     "affected. Revenue is being lost. There is no workaround. What priority is this "
     "and what do we do?"),
    ("change",
     "I need to push an emergency hotfix for the auth service tonight at 22:00 UTC. "
     "The fix has been validated in staging. Walk me through the CAB approval path."),
    ("problem",
     "We have had 4 incidents in the last 60 days caused by the payment DB connection "
     "pool. Should we open a problem record and what RCA method should we use?"),
    ("service",
     "I need monitoring and incident-management read access for 3 emergency "
     "contractors helping us with the Black Friday war room. Fastest path?"),
    ("sla",
     "Our P2 SLA compliance dropped to 78% this month against a 95% target. What "
     "does that mean and what actions should we take?"),
]

_OVERRIDE_Q = os.getenv("CANARY_QUESTION", "").strip()


def pick_question() -> tuple[str, str]:
    """Return (expected_agent, prompt) for this canary run.

    Rotation is keyed off the wall clock so multiple replicas / restarts
    don't all land on the same prompt: floor(now / cadence) % N picks the
    bucket.  The cadence (10 min) matches the CronJob schedule, so each
    run advances by one.
    """
    if _OVERRIDE_Q:
        return ("?", _OVERRIDE_Q)
    cadence = 600  # seconds — must match the CronJob schedule
    idx = int(time.time() // cadence) % len(CANARY_QUESTIONS)
    return CANARY_QUESTIONS[idx]


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

    url = f"{SVC_URL}/api/chat"
    expected_agent, canary_q = pick_question()
    status = "ok"
    latency_ms = 0.0
    actual_agent = "unknown"

    with tracer.start_as_current_span(
        "sdc.canary.probe",
        attributes={
            "canary.url":            url,
            "canary.question":       canary_q[:200],
            "canary.expected_agent": expected_agent,
            "canary.timeout":        TIMEOUT_SECS,
        },
    ) as span:
        t0 = time.perf_counter()
        try:
            resp = _requests.post(
                url,
                json={"message": canary_q},
                timeout=TIMEOUT_SECS,
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            if resp.status_code == 200:
                data         = resp.json()
                actual_agent = data.get("agent", "unknown")
                routed_ok    = (expected_agent == "?") or (actual_agent == expected_agent)
                span.set_attribute("canary.status",            "ok")
                span.set_attribute("canary.http_status",       resp.status_code)
                span.set_attribute("canary.latency_ms",        round(latency_ms, 1))
                span.set_attribute("canary.agent",             actual_agent)
                span.set_attribute("canary.routed_correctly",  routed_ok)
                span.set_attribute("canary.response_len",      len(data.get("response", "")))
                span.set_status(StatusCode.OK)
                logger.info(
                    "✅ Canary OK  expected=%s actual=%s routed_ok=%s latency_ms=%.0f",
                    expected_agent, actual_agent, routed_ok, latency_ms,
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
            span.set_attribute("canary.status",     "timeout")
            span.set_attribute("canary.latency_ms", round(latency_ms, 1))
            span.record_exception(TimeoutError(f"No response within {TIMEOUT_SECS}s"))
            span.set_status(StatusCode.ERROR, f"Timeout after {TIMEOUT_SECS}s")
            logger.error("⏱  Canary TIMEOUT after %ds expected=%s url=%s",
                         TIMEOUT_SECS, expected_agent, url)

        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            status = "error"
            span.set_attribute("canary.status",     "error")
            span.set_attribute("canary.latency_ms", round(latency_ms, 1))
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            logger.error("❌ Canary error: %s expected=%s url=%s", exc, expected_agent, url)

        # Emit metrics — labelled with the rotated prompt's expected agent so
        # Dash0 can show per-agent canary latency & success rate panels.
        attrs = {
            "canary.status":         status,
            "canary.expected_agent": expected_agent,
            "canary.actual_agent":   actual_agent,
        }
        lat_hist.record(latency_ms, attrs)
        req_ctr.add(1, attrs)
        up_gauge.set(0.0 if status != "ok" else 1.0, {"canary.expected_agent": expected_agent})

    # Shutdown flushes the BatchSpanProcessor and triggers a final metric export
    tp.shutdown()
    mp.shutdown()

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(run())
