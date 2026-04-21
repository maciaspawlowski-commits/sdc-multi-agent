"""Simple LLM chat app — instrumented with OpenTelemetry + LLMetry, monitored by Dash0.

Uses Ollama for fully local, free inference (no API keys required).
Install Ollama: https://ollama.com  →  ollama pull llama3.2

LLM calls are auto-instrumented via LLMetry (Traceloop's opentelemetry-instrumentation-openai).
The OpenAI SDK is pointed at Ollama's OpenAI-compatible local endpoint — no OpenAI account needed.
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx

_SYNTHETIC_PROMPTS = [
    "What are the trade-offs between head-based and tail-based trace sampling strategies in high-throughput distributed systems?",
    "How does the OpenTelemetry Collector's processor pipeline differ from SDK-side processing, and when should you prefer each?",
    "Explain how exemplars bridge the gap between metrics and traces in Prometheus and OpenTelemetry.",
    "What are the cardinality pitfalls when designing metric label sets, and how do they affect TSDB performance?",
    "How does W3C Trace Context propagation differ from B3 propagation, and what are the migration risks?",
    "When should you use a histogram vs a summary metric, and what are the aggregation semantics differences in OpenTelemetry?",
    "Describe the cold-start observability problem in serverless and how OTel instrumentation needs to adapt.",
    "What is the difference between push-based and pull-based metrics collection, and how does the OTel Collector bridge both?",
    "How do you design a meaningful SLO using error budget burn rate alerts without generating alert fatigue?",
    "What are the observability implications of eventual consistency in distributed datastores, and how do you trace across async boundaries?",
    "Compare RED, USE, and GOLDEN SIGNALS methodologies — when would you apply each in an LLM serving platform?",
    "How does context propagation work across message queue boundaries in async architectures, and what OTel conventions apply?",
    "What are the semantic conventions for GenAI observability in OpenTelemetry, and how mature is the spec today?",
    "Explain the differences between span events, span links, and child spans — when is each the right modelling choice?",
    "How do you instrument a streaming LLM response (server-sent events) with OpenTelemetry without losing token-level telemetry?",
    "What is the role of the Resource in OTel, and how does it differ from span attributes for infrastructure correlation?",
    "How do you detect and alert on LLM prompt injection attempts using observability data alone?",
    "What are the observability challenges of multi-tenant LLM deployments, and how do you isolate per-tenant signals?",
]

_SYNTHETIC_ERRORS = [
    ("TimeoutError", "LLM request timed out after 30s"),
    ("ConnectionError", "Failed to connect to model backend"),
    ("RateLimitError", "Rate limit exceeded — too many requests"),
    ("ModelUnavailableError", "Requested model is not available"),
    ("ContextLengthError", "Prompt exceeds maximum context length"),
]

_ERROR_RATE = float(os.getenv("SYNTHETIC_ERROR_RATE", "0.2"))  # 20% chance of error
APP_VERSION = os.getenv("APP_VERSION", "6.1.0")

_SYNTHETIC_INTERVAL = int(os.getenv("SYNTHETIC_INTERVAL_SECONDS", "5"))

import json
from asyncio import Queue

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from openai import OpenAI
from opentelemetry import baggage, context, metrics, trace
from pydantic import BaseModel

# SSE subscribers — each connected browser tab gets its own queue
_feed_subscribers: list[Queue] = []


def _broadcast(event: dict) -> None:
    payload = f"data: {json.dumps(event)}\n\n"
    for q in _feed_subscribers:
        q.put_nowait(payload)


_PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://localhost:8001")


async def _processor(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """Call the processor service — fully async so it never blocks the event loop."""
    with _tracer.start_as_current_span(
        f"processor{path}",
        kind=trace.SpanKind.CLIENT,
        attributes={
            "peer.service": "llm-processor",
            "http.method": "POST",
            "http.url": f"{_PROCESSOR_URL}{path}",
        },
    ):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{_PROCESSOR_URL}{path}", json=body, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("processor %s failed: %s — skipping", path, exc)
            return body  # degrade gracefully

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

# OTel instruments — populated in lifespan after providers are configured
_tracer: Optional[trace.Tracer] = None
_token_counter: Optional[metrics.Counter] = None
_duration_hist: Optional[metrics.Histogram] = None
_request_counter: Optional[metrics.Counter] = None

# Sync OpenAI client — LLMetry instruments this; calls run via asyncio.to_thread for concurrency
_llm_client: Optional[OpenAI] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tracer, _token_counter, _duration_hist, _request_counter, _llm_client

    from otel import setup_telemetry
    setup_telemetry(app, service_version=APP_VERSION)

    _tracer = trace.get_tracer("llm-demo")
    meter = metrics.get_meter("llm-demo")
    _token_counter = meter.create_counter(
        "gen_ai.token.usage",
        unit="tokens",
        description="LLM token usage (input + output)",
    )
    _duration_hist = meter.create_histogram(
        "gen_ai.request.duration",
        unit="ms",
        description="End-to-end LLM request duration",
    )
    _request_counter = meter.create_counter(
        "gen_ai.requests",
        unit="requests",
        description="Total LLM chat requests",
    )

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    _llm_client = OpenAI(
        base_url=f"{ollama_host}/v1",
        api_key="ollama",  # required by the SDK, ignored by Ollama
    )

    model = os.getenv("LLM_MODEL", "llama3.2")
    logger.info("LLM Demo ready — http://localhost:8000  (model: %s, via LLMetry)", model)

    task = asyncio.create_task(_synthetic_traffic_loop())
    yield
    task.cancel()
    logger.info("LLM Demo shutting down")


async def _synthetic_traffic_loop():
    """Generate periodic LLM requests to keep Dash0 charts and dependency map populated."""
    await asyncio.sleep(5)  # let startup finish first
    while True:
        try:
            prompt = random.choice(_SYNTHETIC_PROMPTS)
            model = os.getenv("LLM_MODEL", "llama3.2")
            attrs = {"gen_ai.system": "ollama", "gen_ai.request.model": model}

            ctx = baggage.set_baggage("session.id", "synthetic")
            ctx = baggage.set_baggage("traffic.type", "synthetic", context=ctx)
            tok = context.attach(ctx)

            try:
                with _tracer.start_as_current_span("llm.chat") as span:
                    span.set_attribute("session.id", "synthetic")
                    span.set_attribute("traffic.type", "synthetic")
                    span.set_attribute("gen_ai.request.model", model)

                    t0 = time.perf_counter()
                    logger.info("synthetic traffic: prompt=%r", prompt[:60])

                    # Simulate random errors (~20% of requests)
                    if random.random() < _ERROR_RATE:
                        err_type, err_msg = random.choice(_SYNTHETIC_ERRORS)
                        latency_ms = (time.perf_counter() - t0) * 1000 + random.uniform(50, 800)
                        span.set_attribute("error.type", err_type)
                        span.record_exception(Exception(err_msg))
                        _request_counter.add(1, {**attrs, "status": "error"})
                        _duration_hist.record(latency_ms, {**attrs, "error": "true"})
                        logger.error("synthetic error type=%s msg=%s", err_type, err_msg)
                        _broadcast({"prompt": prompt, "error": err_msg, "error_type": err_type,
                                    "latency_ms": round(latency_ms, 1)})
                        continue

                    pre = await _processor("/pre", {"prompt": prompt, "session_id": "synthetic"})
                    clean_prompt = pre.get("prompt", prompt)

                    response = await asyncio.to_thread(_llm_client.chat.completions.create,
                        model=model,
                        messages=[{"role": "user", "content": clean_prompt}],
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000

                    input_tokens = response.usage.prompt_tokens if response.usage else 0
                    output_tokens = response.usage.completion_tokens if response.usage else 0
                    raw_content = response.choices[0].message.content or ""

                    post = await _processor("/post", {"response": raw_content, "session_id": "synthetic"})

                    _request_counter.add(1, {**attrs, "status": "ok"})
                    if input_tokens:
                        _token_counter.add(input_tokens, {**attrs, "gen_ai.token.type": "input"})
                    _token_counter.add(output_tokens, {**attrs, "gen_ai.token.type": "output"})
                    _duration_hist.record(latency_ms, attrs)

                    logger.info(
                        "synthetic traffic ok in=%d out=%d latency_ms=%.0f sentiment=%s",
                        input_tokens, output_tokens, latency_ms, post.get("sentiment", "?"),
                    )

                    _broadcast({
                        "prompt": prompt,
                        "response": raw_content,
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "latency_ms": round(latency_ms, 1),
                        "sentiment": post.get("sentiment", ""),
                        "reading_time_s": post.get("reading_time_s", 0),
                    })
            finally:
                context.detach(tok)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("synthetic traffic failed: %s", exc)

        await asyncio.sleep(_SYNTHETIC_INTERVAL)


app = FastAPI(title="LLM Demo · Dash0", lifespan=lifespan)


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    system: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    session_id: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui():
    return _HTML_PAGE.replace("__APP_VERSION__", APP_VERSION)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/feed")
async def feed():
    """SSE stream — pushes synthetic LLM events to connected browser tabs."""
    q: Queue = Queue()
    _feed_subscribers.append(q)

    async def stream():
        try:
            while True:
                payload = await q.get()
                yield payload
        finally:
            _feed_subscribers.remove(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, http_req: Request):
    model = os.getenv("LLM_MODEL", "llama3.2")

    # ── Baggage: carry session identity through the entire request context ──
    session_id = http_req.headers.get("X-Session-ID") or str(uuid.uuid4())
    environment = os.getenv("ENVIRONMENT", "local")

    ctx = baggage.set_baggage("session.id", session_id)
    ctx = baggage.set_baggage("model", model, context=ctx)
    ctx = baggage.set_baggage("environment", environment, context=ctx)
    token = context.attach(ctx)

    attrs = {"gen_ai.system": "ollama", "gen_ai.request.model": model}

    try:
        with _tracer.start_as_current_span("llm.chat") as span:
            span.set_attribute("session.id", session_id)
            span.set_attribute("deployment.environment", environment)
            span.set_attribute("gen_ai.request.model", model)

            t0 = time.perf_counter()

            logger.info(
                "chat request started session=%s model=%s prompt_len=%d",
                session_id, model, len(req.message),
            )

            try:
                # ── Pre-process: sanitise + enrich prompt ─────────────────
                pre = await _processor("/pre", {"prompt": req.message, "session_id": session_id})
                clean_prompt = pre.get("prompt", req.message)

                messages = [{"role": "user", "content": clean_prompt}]
                if req.system:
                    messages.insert(0, {"role": "system", "content": req.system})

                # LLMetry automatically creates a child span with GenAI attributes
                response = await asyncio.to_thread(
                    _llm_client.chat.completions.create,
                    model=model,
                    messages=messages,
                )
                latency_ms = (time.perf_counter() - t0) * 1000

                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = response.usage.completion_tokens if response.usage else 0
                raw_content = response.choices[0].message.content or ""

                # ── Post-process: enrich response with metadata ───────────
                post = await _processor("/post", {"response": raw_content, "session_id": session_id})
                content = post.get("response", raw_content)
                span.set_attribute("response.sentiment", post.get("sentiment", "unknown"))
                span.set_attribute("response.reading_time_s", post.get("reading_time_s", 0))

                # Metrics
                _request_counter.add(1, {**attrs, "status": "ok"})
                if input_tokens:
                    _token_counter.add(input_tokens, {**attrs, "gen_ai.token.type": "input"})
                _token_counter.add(output_tokens, {**attrs, "gen_ai.token.type": "output"})
                _duration_hist.record(latency_ms, attrs)

                logger.info(
                    "chat ok session=%s model=%s in=%d out=%d latency_ms=%.0f sentiment=%s",
                    session_id, model, input_tokens, output_tokens, latency_ms,
                    post.get("sentiment", "?"),
                )

                return ChatResponse(
                    response=content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=round(latency_ms, 1),
                    session_id=session_id,
                )

            except Exception as exc:
                latency_ms = (time.perf_counter() - t0) * 1000
                span.record_exception(exc)
                span.set_attribute("error.type", type(exc).__name__)
                _request_counter.add(1, {**attrs, "status": "error"})
                _duration_hist.record(latency_ms, {**attrs, "error": "true"})
                logger.error(
                    "chat failed session=%s model=%s error=%s",
                    session_id, model, exc,
                )
                raise HTTPException(status_code=502, detail=str(exc))

    finally:
        context.detach(token)


# ── Embedded chat UI ─────────────────────────────────────────────────────────

_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM Demo · Dash0 Observability</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #0f1117; color: #e2e8f0; height: 100vh; display: flex; flex-direction: column; align-items: center; }
header { width: 100%; max-width: 800px; padding: 18px 20px; border-bottom: 1px solid #1e2a3a; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
header h1 { font-size: 1.1rem; font-weight: 600; }
.badge { background: #0f62fe; color: white; font-size: 0.68rem; padding: 3px 9px; border-radius: 999px; letter-spacing: .02em; }
.badge.version { background: #374151; font-family: monospace; }
.badge.local { background: #059669; }
.badge.llmetry { background: #d97706; }
.badge.session { background: #7c3aed; font-family: monospace; }
#chat { flex: 1; width: 100%; max-width: 800px; overflow-y: auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 16px; }
.msg { max-width: 82%; padding: 12px 16px; border-radius: 14px; line-height: 1.55; word-break: break-word; }
.user { align-self: flex-end; background: #0f62fe; color: white; border-bottom-right-radius: 4px; }
.assistant { align-self: flex-start; background: #1a2232; border-bottom-left-radius: 4px; }
.synthetic-q { align-self: flex-end; background: #1a2e1a; color: #86efac; border: 1px solid #166534; border-bottom-right-radius: 4px; font-style: italic; opacity: 0.75; }
.synthetic-a { align-self: flex-start; background: #1a2e1a; color: #bbf7d0; border: 1px solid #166534; border-bottom-left-radius: 4px; opacity: 0.75; }
.meta { font-size: 0.68rem; opacity: 0.45; margin-top: 7px; font-family: monospace; }
footer { width: 100%; max-width: 800px; padding: 14px 20px; border-top: 1px solid #1e2a3a; display: flex; gap: 10px; }
#input { flex: 1; background: #1a2232; border: 1px solid #2d3a4f; border-radius: 10px; padding: 11px 15px; color: #e2e8f0; font-size: 0.95rem; outline: none; transition: border-color .15s; }
#input:focus { border-color: #0f62fe; }
button { background: #0f62fe; color: white; border: none; border-radius: 10px; padding: 11px 20px; cursor: pointer; font-size: 0.95rem; font-weight: 500; transition: background .15s; }
button:hover { background: #0353d9; }
button:disabled { opacity: 0.4; cursor: default; }
.thinking { opacity: 0.5; font-style: italic; animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:.3} 50%{opacity:.7} }
</style>
</head>
<body>
<header>
  <h1>🤖 LLM Demo</h1>
  <span class="badge version">v__APP_VERSION__</span>
  <span class="badge local">Local · Ollama</span>
  <span class="badge llmetry">LLMetry</span>
  <span class="badge">Traces</span>
  <span class="badge">Metrics</span>
  <span class="badge">Logs</span>
  <span class="badge">Baggage</span>
  <span class="badge session" id="session-badge">session: …</span>
</header>
<div id="chat">
  <div class="msg assistant">
    👋 Hi! I'm running locally via Ollama — <strong>no API costs</strong>. Every message is auto-instrumented by <strong>LLMetry</strong> and sent to Dash0 as correlated traces, metrics, and logs.
    <div class="meta">LLMetry · Traces · Metrics · Logs · Baggage · 100% local inference</div>
  </div>
</div>
<footer>
  <input id="input" type="text" placeholder="Ask me anything… (runs locally)" autofocus autocomplete="off">
  <button id="btn" onclick="send()">Send</button>
</footer>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const btn = document.getElementById('btn');

// Persist session ID across page refreshes so all messages share the same baggage
let sessionId = localStorage.getItem('llm_session_id');
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem('llm_session_id', sessionId);
}
document.getElementById('session-badge').textContent = 'session: ' + sessionId.slice(0, 8) + '…';

input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

// SSE — receive synthetic traffic events from the server
const evtSource = new EventSource('/api/feed');
evtSource.onmessage = (e) => {
  const d = JSON.parse(e.data);
  addMsg('synthetic-q', '🤖 <em>[synthetic]</em> ' + escHtml(d.prompt));
  if (d.error) {
    addMsg('synthetic-a',
      `<span style="color:#f87171">⚠ ${escHtml(d.error_type)}: ${escHtml(d.error)}</span>`,
      `error · ${d.latency_ms}ms · synthetic`);
  } else {
    const meta = `${d.model} · ${d.input_tokens} in / ${d.output_tokens} out · ${d.latency_ms}ms` +
      (d.sentiment ? ` · ${d.sentiment}` : '') +
      (d.reading_time_s ? ` · ${d.reading_time_s}s read` : '') + ' · synthetic';
    addMsg('synthetic-a', escHtml(d.response).replace(/\\n/g, '<br>'), meta);
  }
};

function addMsg(role, html, meta) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = `<div>${html}</div>` + (meta !== undefined ? `<div class="meta">${meta}</div>` : '');
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function send() {
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  input.focus();
  addMsg('user', escHtml(msg));
  const pending = addMsg('assistant', '<span class="thinking">Thinking…</span>', '');

  // fire-and-forget — no lock, multiple requests can be in-flight simultaneously
  fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
    },
    body: JSON.stringify({ message: msg }),
  }).then(res => res.json().then(data => ({ ok: res.ok, data }))).then(({ ok, data }) => {
    if (!ok) throw new Error(data.detail || 'Request failed');
    pending.querySelector('div').innerHTML = escHtml(data.response).replace(/\\n/g, '<br>');
    pending.querySelector('.meta').textContent =
      `${data.model} · ${data.input_tokens} in / ${data.output_tokens} out · ${data.latency_ms}ms · session: ${data.session_id.slice(0,8)}…`;
  }).catch(err => {
    pending.querySelector('div').innerHTML = `<span style="color:#f87171">Error: ${escHtml(err.message)}</span>`;
    pending.querySelector('.meta').textContent = '';
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    import subprocess
    import sys
    import uvicorn
    from pathlib import Path

    processor_proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "processor.py")],
        env=os.environ.copy(),
    )
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    finally:
        processor_proc.terminate()
        processor_proc.wait()
