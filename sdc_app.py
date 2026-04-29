"""SDC Multi-Agent System — LangGraph + Ollama + FastAPI.

Six-agent architecture:
  Orchestrator  →  routes to one of:
    • Incident Response Agent
    • Change Management Agent
    • Problem Management Agent
    • Service Request Agent
    • SLA Monitoring Agent

Observability:
  • OTel traces + metrics + logs  → Dash0  (via sdc_otel.py)
  • LangChain / ChatOllama calls  → Dash0  (LLMetry/LangChain instrumentor)
  • LangGraph graph traces        → LangSmith  (via LANGCHAIN_TRACING_V2 env var)
  Both platforms receive data simultaneously with zero conflict.
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from langchain_core.messages import HumanMessage, messages_from_dict, messages_to_dict
from opentelemetry import baggage, metrics, trace
from opentelemetry.context import attach, detach
from pydantic import BaseModel

from sdc import chaos as chaos_module
from sdc.chaos import ChaosCallback
from sdc.graph import sdc_graph
from sdc.simulation.black_friday import get_black_friday_steps
from sdc.state import AGENT_ICONS, AGENT_NAMES
from sdc_otel import SDCToolsCallback

# Singleton callback — created once, reused across all requests so metric
# instruments are only registered once (lazy inside SDCToolsCallback).
_tools_callback = SDCToolsCallback()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

APP_VERSION = os.getenv("APP_VERSION", "5.0.0")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "86400"))  # 24 h default

# OTel instruments — populated in lifespan
_tracer: Optional[trace.Tracer] = None
_agent_counter: Optional[metrics.Counter] = None
_latency_hist: Optional[metrics.Histogram] = None
_error_counter: Optional[metrics.Counter] = None

# Redis client — initialised lazily on first use
_redis: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def _load_session(session_id: str) -> list:
    """Load message history from Redis; returns [] if no session exists."""
    try:
        r = await _get_redis()
        raw = await r.get(f"sdc:session:{session_id}")
        if not raw:
            return []
        return messages_from_dict(json.loads(raw))
    except Exception as exc:
        logger.warning("session load failed id=%s error=%s — starting fresh", session_id, exc)
        return []


async def _save_session(session_id: str, messages: list) -> None:
    """Serialise and persist message history to Redis with TTL."""
    try:
        r = await _get_redis()
        payload = json.dumps(messages_to_dict(messages))
        await r.set(f"sdc:session:{session_id}", payload, ex=SESSION_TTL)
    except Exception as exc:
        logger.warning("session save failed id=%s error=%s", session_id, exc)


async def _delete_session(session_id: str) -> None:
    """Remove a session from Redis."""
    try:
        r = await _get_redis()
        await r.delete(f"sdc:session:{session_id}")
    except Exception as exc:
        logger.warning("session delete failed id=%s error=%s", session_id, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tracer, _agent_counter, _latency_hist, _error_counter

    from sdc_otel import setup_sdc_telemetry
    setup_sdc_telemetry(app, service_version=APP_VERSION)

    _tracer = trace.get_tracer("sdc-agents")
    meter = metrics.get_meter("sdc-agents")

    _agent_counter = meter.create_counter(
        "sdc.agent.requests",
        unit="requests",
        description="Total requests handled per SDC specialist agent",
    )
    _latency_hist = meter.create_histogram(
        "sdc.agent.latency",
        unit="ms",
        description="End-to-end latency per agent invocation",
    )
    _error_counter = meter.create_counter(
        "sdc.agent.errors",
        unit="errors",
        description="Agent invocation errors",
    )

    # Verify Redis connectivity (non-fatal — app degrades gracefully)
    try:
        await (await _get_redis()).ping()
        logger.info("Redis OK — %s", REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — sessions will not persist across replicas", exc)

    logger.info(
        "SDC Multi-Agent System ready — http://localhost:8000  (model: %s @ %s)",
        LLM_MODEL, OLLAMA_HOST,
    )
    yield
    logger.info("SDC Multi-Agent System shutting down")


app = FastAPI(title="SDC Multi-Agent System", lifespan=lifespan)


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    agent_name: str
    agent_icon: str
    routing_reason: str
    session_id: str
    model: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui():
    return _build_html()


@app.get("/health")
def health():
    from sdc.vectorstore import collection_stats
    return {
        "status": "ok",
        "model": LLM_MODEL,
        "agents": list(AGENT_NAMES.keys()),
        "knowledge_base": collection_stats(),
        "chaos": chaos_module.get_state(),
    }


# ── Chaos endpoints ──────────────────────────────────────────────────────────

class ChaosRequest(BaseModel):
    mode: str
    probability: float = 0.5
    delay_ms: int = 3000


@app.get("/api/chaos")
def get_chaos():
    """Return current chaos configuration."""
    return chaos_module.get_state()


@app.post("/api/chaos")
def set_chaos(req: ChaosRequest):
    """Activate a chaos mode. Immediately affects all subsequent agent requests."""
    try:
        return chaos_module.set_mode(req.mode, req.probability, req.delay_ms)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/chaos")
def reset_chaos():
    """Disable chaos — restore normal operation."""
    return chaos_module.reset()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    t0 = time.perf_counter()

    with _tracer.start_as_current_span(
        "sdc.agent.session",
        kind=trace.SpanKind.SERVER,
        attributes={
            "session.id": session_id,
            "llm.model": LLM_MODEL,
            "sdc.message.length": len(req.message),
        },
    ) as span:
        history = await _load_session(session_id)
        history.append(HumanMessage(content=req.message))

        initial_state = {
            "messages": history,
            "current_agent": None,
            "routing_reason": None,
        }

        # Propagate session.id via OTel baggage so every child span gets it
        _baggage_token = attach(baggage.set_baggage("session.id", session_id))
        try:
            result = await sdc_graph.ainvoke(
                initial_state,
                config={"callbacks": [_tools_callback, ChaosCallback()]},
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            span.record_exception(exc)
            span.set_attribute("error.type", type(exc).__name__)
            _error_counter.add(1, {"sdc.agent": "unknown", "llm.model": LLM_MODEL})
            _latency_hist.record(latency_ms, {"sdc.agent": "unknown", "status": "error"})
            logger.error("Graph invocation failed session=%s error=%s", session_id, exc)
            raise HTTPException(status_code=502, detail=f"Agent error: {exc}")
        finally:
            detach(_baggage_token)

        ai_messages = [m for m in result["messages"] if hasattr(m, "type") and m.type == "ai"]
        if not ai_messages:
            raise HTTPException(status_code=502, detail="No response from agent")

        last_ai = ai_messages[-1]
        agent = result.get("current_agent", "incident")
        routing_reason = result.get("routing_reason", "")
        latency_ms = (time.perf_counter() - t0) * 1000

        # Enrich the root span with routing outcome
        span.set_attribute("sdc.agent", agent)
        span.set_attribute("sdc.agent.name", AGENT_NAMES.get(agent, agent))
        span.set_attribute("sdc.routing.reason", routing_reason)
        span.set_attribute("sdc.latency_ms", round(latency_ms, 1))

        # Metrics
        attrs = {"sdc.agent": agent, "llm.model": LLM_MODEL}
        _agent_counter.add(1, attrs)
        _latency_hist.record(latency_ms, {**attrs, "status": "ok"})

        # Persist full conversation for multi-turn
        await _save_session(session_id, list(result["messages"]))

        logger.info(
            "chat ok session=%s agent=%s model=%s latency_ms=%.0f routing=%s",
            session_id, agent, LLM_MODEL, latency_ms, routing_reason,
        )

        return ChatResponse(
            response=last_ai.content,
            agent=agent,
            agent_name=AGENT_NAMES.get(agent, agent),
            agent_icon=AGENT_ICONS.get(agent, "🤖"),
            routing_reason=routing_reason,
            session_id=session_id,
            model=LLM_MODEL,
        )


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    await _delete_session(session_id)
    return {"cleared": session_id}


@app.post("/api/simulate/black-friday")
async def simulate_black_friday():
    """Stream a Black Friday scenario as server-sent events.

    Each event is a JSON object on a ``data:`` line.  Event types:
      • ``step_start``   — step is about to run (description + query)
      • ``step_end``     — step completed (agent, response, latency_ms)
      • ``error``        — step failed (error message)
      • ``sim_complete`` — all steps finished
    """
    sim_session_id = str(uuid.uuid4())
    steps = get_black_friday_steps()

    async def event_stream():
        for i, step in enumerate(steps, 1):
            # ── announce step ────────────────────────────────────────────────
            yield (
                "data: "
                + json.dumps({
                    "type":        "step_start",
                    "step":        i,
                    "total":       len(steps),
                    "description": step["description"],
                    "query":       step["query"],
                })
                + "\n\n"
            )

            # ── run the agent graph ─────────────────────────────────────────
            try:
                history = await _load_session(sim_session_id)
                history.append(HumanMessage(content=step["query"]))

                t0 = time.perf_counter()
                _sim_token = attach(baggage.set_baggage("session.id", sim_session_id))
                try:
                    result = await sdc_graph.ainvoke(
                        {
                            "messages":       history,
                            "current_agent":  None,
                            "routing_reason": None,
                        },
                        config={"callbacks": [_tools_callback, ChaosCallback()]},
                    )
                finally:
                    detach(_sim_token)
                latency_ms = round((time.perf_counter() - t0) * 1000)

                # Persist growing conversation history
                await _save_session(sim_session_id, list(result["messages"]))

                ai_msgs = [
                    m for m in result["messages"]
                    if hasattr(m, "type") and m.type == "ai"
                ]
                last_ai   = ai_msgs[-1] if ai_msgs else None
                agent     = result.get("current_agent", "incident")
                reason    = result.get("routing_reason", "")

                # Emit OTel metric for the simulation request
                if _agent_counter:
                    _agent_counter.add(1, {"sdc.agent": agent, "llm.model": LLM_MODEL, "sdc.sim": "black_friday"})
                if _latency_hist:
                    _latency_hist.record(latency_ms, {"sdc.agent": agent, "status": "ok", "sdc.sim": "black_friday"})

                logger.info(
                    "sim step=%d/%d agent=%s latency_ms=%d session=%s",
                    i, len(steps), agent, latency_ms, sim_session_id,
                )

                yield (
                    "data: "
                    + json.dumps({
                        "type":        "step_end",
                        "step":        i,
                        "total":       len(steps),
                        "agent":       agent,
                        "agent_name":  AGENT_NAMES.get(agent, agent),
                        "agent_icon":  AGENT_ICONS.get(agent, "🤖"),
                        "routing_reason": reason,
                        "response":    last_ai.content if last_ai else "",
                        "latency_ms":  latency_ms,
                    })
                    + "\n\n"
                )

            except Exception as exc:
                logger.error(
                    "sim error step=%d session=%s error=%s", i, sim_session_id, exc
                )
                yield (
                    "data: "
                    + json.dumps({
                        "type":  "error",
                        "step":  i,
                        "error": str(exc),
                    })
                    + "\n\n"
                )

            # Small pause so the client can render before the next heavy LLM call
            await asyncio.sleep(0.3)

        # ── all done ─────────────────────────────────────────────────────────
        await _delete_session(sim_session_id)  # clean up sim session
        yield (
            "data: "
            + json.dumps({
                "type":        "sim_complete",
                "total_steps": len(steps),
                "session_id":  sim_session_id,
            })
            + "\n\n"
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


# ── Embedded HTML/JS frontend ────────────────────────────────────────────────

def _build_html() -> str:
    agents_js = []
    for key, name in AGENT_NAMES.items():
        icon = AGENT_ICONS.get(key, "🤖")
        agents_js.append(f'{{"id":"{key}","name":"{name}","icon":"{icon}"}}')
    agents_json = "[" + ",".join(agents_js) + "]"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SDC Multi-Agent System</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg: #0d1117; --surface: #161b22; --border: #21262d;
  --accent: #238636; --accent-hover: #2ea043;
  --blue: #1f6feb; --text: #c9d1d9; --muted: #8b949e;
  --p1: #f85149; --p2: #e3b341; --p3: #3fb950; --p4: #58a6ff;
}}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}

/* ── Top bar ── */
.topbar {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 20px; display: flex; align-items: center; gap: 16px; flex-shrink: 0; }}
.topbar h1 {{ font-size: 1rem; font-weight: 600; letter-spacing: .02em; }}
.badge {{ display: inline-flex; align-items: center; gap: 4px; font-size: 0.7rem; padding: 2px 8px; border-radius: 20px; font-weight: 500; border: 1px solid; }}
.badge-green {{ color: #3fb950; border-color: #238636; background: rgba(56,139,53,.15); }}
.badge-blue  {{ color: #58a6ff; border-color: #1f6feb; background: rgba(31,111,235,.15); }}
.badge-orange{{ color: #e3b341; border-color: #d29922; background: rgba(187,128,9,.15); }}
.badge-purple{{ color: #bc8cff; border-color: #8957e5; background: rgba(137,87,229,.15); }}

/* ── Layout ── */
.layout {{ display: flex; flex: 1; overflow: hidden; }}

/* ── Agent sidebar ── */
.sidebar {{ width: 220px; flex-shrink: 0; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow-y: auto; }}
.sidebar-header {{ padding: 12px 14px; font-size: 0.7rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; border-bottom: 1px solid var(--border); }}
.agent-card {{ padding: 12px 14px; border-bottom: 1px solid var(--border); cursor: default; transition: background .15s; }}
.agent-card.active {{ background: rgba(35,134,54,.12); border-left: 3px solid var(--accent); padding-left: 11px; }}
.agent-card .agent-icon {{ font-size: 1.2rem; margin-bottom: 4px; }}
.agent-card .agent-name {{ font-size: 0.78rem; font-weight: 600; line-height: 1.3; }}
.agent-card .agent-status {{ font-size: 0.68rem; color: var(--muted); margin-top: 3px; }}
.agent-card.active .agent-status {{ color: #3fb950; }}
.orchestrator-card {{ padding: 12px 14px; border-bottom: 1px solid var(--border); background: rgba(31,111,235,.08); }}
.orchestrator-card .agent-icon {{ font-size: 1.2rem; margin-bottom: 4px; }}
.orchestrator-card .agent-name {{ font-size: 0.78rem; font-weight: 600; color: #58a6ff; }}
.orchestrator-card .agent-status {{ font-size: 0.68rem; color: var(--muted); margin-top: 3px; }}
.routing-badge {{ display: inline-block; font-size: 0.6rem; background: rgba(31,111,235,.25); color: #58a6ff; border-radius: 4px; padding: 1px 5px; margin-top: 4px; }}

/* ── Chat main ── */
.main {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
.chat-area {{ flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }}
.msg {{ max-width: 75%; word-break: break-word; }}
.msg.user {{ align-self: flex-end; }}
.msg.assistant {{ align-self: flex-start; }}
.msg-bubble {{ padding: 11px 15px; border-radius: 12px; line-height: 1.6; font-size: 0.88rem; }}
.msg.user .msg-bubble {{ background: var(--blue); color: white; border-bottom-right-radius: 3px; }}
.msg.assistant .msg-bubble {{ background: var(--surface); border: 1px solid var(--border); border-bottom-left-radius: 3px; white-space: pre-wrap; }}
.msg-meta {{ font-size: 0.65rem; color: var(--muted); margin-top: 5px; display: flex; align-items: center; gap: 6px; }}
.msg.user .msg-meta {{ justify-content: flex-end; }}
.agent-tag {{ display: inline-flex; align-items: center; gap: 3px; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 500; }}
.tag-incident {{ background: rgba(248,81,73,.15); color: #f85149; }}
.tag-change   {{ background: rgba(31,111,235,.15); color: #58a6ff; }}
.tag-problem  {{ background: rgba(188,140,255,.15); color: #bc8cff; }}
.tag-service  {{ background: rgba(63,185,80,.15); color: #3fb950; }}
.tag-sla      {{ background: rgba(227,179,65,.15); color: #e3b341; }}
.tag-general  {{ background: rgba(139,148,158,.15); color: #8b949e; }}
.thinking {{ opacity: 0.5; font-style: italic; animation: pulse 1.2s ease-in-out infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:.3}} 50%{{opacity:.7}} }}

/* ── Input bar ── */
.input-bar {{ background: var(--surface); border-top: 1px solid var(--border); padding: 14px 20px; display: flex; gap: 10px; flex-shrink: 0; }}
#input {{ flex: 1; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; color: var(--text); font-size: 0.9rem; outline: none; transition: border-color .15s; resize: none; height: 44px; font-family: inherit; }}
#input:focus {{ border-color: var(--blue); }}
#send-btn {{ background: var(--accent); color: white; border: none; border-radius: 8px; padding: 10px 20px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: background .15s; white-space: nowrap; }}
#send-btn:hover {{ background: var(--accent-hover); }}
#send-btn:disabled {{ opacity: .4; cursor: default; }}
.new-session-btn {{ background: transparent; border: 1px solid var(--border); color: var(--muted); border-radius: 8px; padding: 10px 12px; cursor: pointer; font-size: 0.8rem; transition: all .15s; }}
.new-session-btn:hover {{ border-color: var(--text); color: var(--text); }}

/* ── Welcome ── */
.welcome {{ align-self: center; text-align: center; max-width: 480px; padding: 40px 20px; }}
.welcome h2 {{ font-size: 1.4rem; margin-bottom: 10px; }}
.welcome p {{ color: var(--muted); font-size: 0.85rem; line-height: 1.6; margin-bottom: 20px; }}
.example-prompts {{ display: flex; flex-direction: column; gap: 8px; text-align: left; }}
.prompt-chip {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; font-size: 0.82rem; cursor: pointer; transition: border-color .15s; line-height: 1.4; }}
.prompt-chip:hover {{ border-color: var(--blue); color: var(--text); }}
.prompt-chip .chip-label {{ color: var(--muted); font-size: 0.7rem; margin-bottom: 2px; }}

/* ── Black Friday simulation button ── */
.sim-btn {{
  margin-left: auto; background: rgba(248,81,73,.12); color: #f85149;
  border: 1px solid rgba(248,81,73,.35); border-radius: 8px; padding: 5px 13px;
  cursor: pointer; font-size: 0.78rem; font-weight: 600; letter-spacing: .01em;
  transition: all .15s; white-space: nowrap;
}}
.sim-btn:hover {{ background: rgba(248,81,73,.22); border-color: rgba(248,81,73,.6); }}
.sim-btn:disabled {{ opacity: .4; cursor: default; }}

/* ── Simulation overlay (full-screen backdrop) ── */
.sim-overlay {{
  position: fixed; inset: 0; background: rgba(0,0,0,.82); backdrop-filter: blur(5px);
  z-index: 200; display: flex; flex-direction: column; align-items: center;
  justify-content: flex-end;
}}
.sim-overlay.hidden {{ display: none; }}

/* ── Simulation panel (bottom sheet) ── */
.sim-panel {{
  background: var(--bg); border: 1px solid var(--border); border-bottom: none;
  border-radius: 16px 16px 0 0; width: 100%; max-width: 980px; height: 88vh;
  display: flex; flex-direction: column; overflow: hidden;
  animation: sim-slide-up .28s cubic-bezier(.22,.68,0,1.2);
}}
@keyframes sim-slide-up {{
  from {{ transform: translateY(60px); opacity: 0; }}
  to   {{ transform: translateY(0);    opacity: 1; }}
}}

/* ── Panel header ── */
.sim-header {{
  background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  padding: 14px 18px; display: flex; align-items: center; gap: 12px;
}}
.sim-header-title {{ font-size: 0.92rem; font-weight: 600; }}
.sim-header-sub {{ font-size: 0.72rem; color: var(--muted); }}
.sim-progress-wrap {{ flex: 1; }}
.sim-progress-track {{
  height: 5px; background: var(--border); border-radius: 3px; overflow: hidden;
}}
.sim-progress-bar {{
  height: 100%; background: #f85149; border-radius: 3px;
  transition: width .45s ease; width: 0%;
}}
.sim-step-counter {{ font-size: 0.72rem; color: var(--muted); margin-top: 4px; text-align: right; }}
.sim-close-btn {{
  background: transparent; border: 1px solid var(--border); color: var(--muted);
  border-radius: 6px; padding: 5px 11px; cursor: pointer; font-size: 0.78rem;
  transition: all .15s;
}}
.sim-close-btn:hover {{ border-color: var(--text); color: var(--text); }}

/* ── Panel body — step timeline ── */
.sim-body {{ flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 28px; }}

.sim-step {{ display: flex; flex-direction: column; gap: 6px; }}

.sim-step-header {{
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}}
.sim-step-num {{
  width: 22px; height: 22px; border-radius: 50%; display: inline-flex;
  align-items: center; justify-content: center; font-size: 0.65rem; font-weight: 700;
  flex-shrink: 0;
  background: var(--border); color: var(--muted); border: 1px solid transparent;
}}
.sim-step-num.running {{
  background: rgba(248,81,73,.18); color: #f85149;
  border-color: rgba(248,81,73,.45); animation: pulse 1.1s ease-in-out infinite;
}}
.sim-step-num.done {{
  background: rgba(56,139,53,.18); color: #3fb950; border-color: rgba(56,139,53,.45);
}}
.sim-step-num.errored {{
  background: rgba(248,81,73,.18); color: #f85149; border-color: rgba(248,81,73,.45);
}}
.sim-step-desc {{ font-size: 0.72rem; color: var(--muted); font-style: italic; }}

.sim-query-bubble {{
  align-self: flex-end; max-width: 78%;
  background: var(--blue); color: #fff; padding: 10px 15px;
  border-radius: 12px 12px 3px 12px; font-size: 0.85rem; line-height: 1.55;
}}
.sim-response-bubble {{
  align-self: flex-start; max-width: 88%;
  background: var(--surface); border: 1px solid var(--border);
  padding: 11px 15px; border-radius: 12px 12px 12px 3px;
  font-size: 0.85rem; line-height: 1.6; white-space: pre-wrap;
}}
.sim-response-bubble.thinking {{
  opacity: .5; font-style: italic; animation: pulse 1.2s ease-in-out infinite;
}}
.sim-response-meta {{
  display: flex; align-items: center; gap: 7px;
  font-size: 0.65rem; color: var(--muted); margin-top: 4px;
}}

.sim-done-banner {{
  text-align: center; padding: 22px; margin-top: 8px;
  background: rgba(56,139,53,.08); border: 1px solid rgba(56,139,53,.28);
  border-radius: 10px; color: #3fb950; font-size: 0.9rem; line-height: 1.7;
}}
.sim-done-banner small {{ display: block; color: var(--muted); font-size: 0.75rem; margin-top: 4px; }}

/* ── Chaos panel ── */
.chaos-toggle-btn {{
  background: transparent; border: 1px solid var(--border); color: var(--muted);
  border-radius: 8px; padding: 5px 13px; cursor: pointer; font-size: 0.78rem;
  font-weight: 600; transition: all .15s; white-space: nowrap;
}}
.chaos-toggle-btn:hover {{ border-color: #f85149; color: #f85149; }}
.chaos-toggle-btn.active {{ background: rgba(248,81,73,.15); border-color: #f85149; color: #f85149; animation: pulse 1.5s ease-in-out infinite; }}

.chaos-panel {{
  background: var(--surface); border-bottom: 2px solid #f85149;
  padding: 12px 20px; flex-shrink: 0;
}}
.chaos-panel.hidden {{ display: none; }}
.chaos-panel-inner {{ max-width: 900px; }}
.chaos-title {{ font-size: 0.85rem; font-weight: 700; color: #f85149; margin-bottom: 2px; }}
.chaos-subtitle {{ font-size: 0.72rem; color: var(--muted); margin-bottom: 10px; }}

.chaos-modes {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
.chaos-mode-btn {{
  background: var(--bg); border: 1px solid var(--border); color: var(--muted);
  border-radius: 6px; padding: 5px 12px; cursor: pointer; font-size: 0.75rem;
  transition: all .15s;
}}
.chaos-mode-btn:hover {{ border-color: var(--text); color: var(--text); }}
.chaos-mode-btn.active {{ background: rgba(248,81,73,.18); border-color: #f85149; color: #f85149; font-weight: 600; }}
.chaos-mode-btn.none {{ color: #3fb950; border-color: #238636; }}
.chaos-mode-btn.none:hover, .chaos-mode-btn.none.active {{ background: rgba(63,185,80,.12); border-color: #3fb950; color: #3fb950; }}

.chaos-options {{ display: flex; gap: 20px; align-items: center; margin-bottom: 8px; font-size: 0.75rem; color: var(--muted); }}
.chaos-options label {{ display: flex; align-items: center; gap: 8px; }}
.chaos-options input[type=range] {{ width: 100px; }}
.chaos-options input[type=number] {{ background: var(--bg); border: 1px solid var(--border); border-radius: 4px; color: var(--text); padding: 3px 6px; width: 80px; font-size: 0.75rem; }}

.chaos-status {{ font-size: 0.72rem; color: var(--muted); font-style: italic; min-height: 16px; }}
.chaos-status.on {{ color: #f85149; font-style: normal; font-weight: 600; }}
</style>
</head>
<body>

<!-- Top bar -->
<div class="topbar">
  <h1>🏢 SDC Multi-Agent System</h1>
  <span class="badge badge-green">● Ollama · {LLM_MODEL}</span>
  <span class="badge badge-blue">LangGraph</span>
  <span class="badge badge-orange">6 Agents</span>
  <span class="badge badge-purple" id="session-badge">session: …</span>
  <button class="sim-btn" id="sim-btn" onclick="openSimulation()" title="Run a scripted Black Friday incident scenario through all five agents">
    🛒 Black Friday Sim
  </button>
  <button class="chaos-toggle-btn" id="chaos-btn" onclick="toggleChaosPanel()" title="Inject failures to test observability">
    🔥 Chaos
  </button>
</div>

<!-- Chaos control panel (inline dropdown) -->
<div class="chaos-panel hidden" id="chaos-panel">
  <div class="chaos-panel-inner">
    <div class="chaos-title">🔥 Chaos Engineering</div>
    <div class="chaos-subtitle">Inject failures — watch them appear in Dash0</div>
    <div class="chaos-modes" id="chaos-modes"></div>
    <div class="chaos-options" id="chaos-options" style="display:none">
      <label>Probability <input type="range" id="chaos-prob" min="0" max="100" value="50"> <span id="chaos-prob-val">50%</span></label>
      <label>Delay (ms) <input type="number" id="chaos-delay" value="3000" min="500" max="15000" step="500"></label>
    </div>
    <div class="chaos-status" id="chaos-status"></div>
  </div>
</div>

<div class="layout">

  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-header">Agents</div>
    <div class="orchestrator-card">
      <div class="agent-icon">🧠</div>
      <div class="agent-name">Orchestrator</div>
      <div class="agent-status" id="orch-status">Ready</div>
      <div class="routing-badge" id="routing-badge" style="display:none"></div>
    </div>
    <div id="agent-list"></div>
  </aside>

  <!-- Chat -->
  <main class="main">
    <div class="chat-area" id="chat">
      <div class="welcome" id="welcome">
        <h2>Welcome to SDC Assistant</h2>
        <p>I route your queries to the right specialist agent — Incident Response, Change Management, Problem Management, Service Requests, or SLA Monitoring.</p>
        <div class="example-prompts">
          <div class="prompt-chip" onclick="fillPrompt(this.dataset.msg)" data-msg="We have a P1 incident — the payment gateway is completely down affecting all customers. What should we do?">
            <div class="chip-label">🚨 Incident Response</div>
            Payment gateway P1 — what are the steps?
          </div>
          <div class="prompt-chip" onclick="fillPrompt(this.dataset.msg)" data-msg="I need to submit an RFC for a database schema migration planned for next Friday evening. What do I need to prepare?">
            <div class="chip-label">🔄 Change Management</div>
            RFC submission for a database migration
          </div>
          <div class="prompt-chip" onclick="fillPrompt(this.dataset.msg)" data-msg="We've had 5 incidents in the last 2 weeks all caused by memory leaks in the API service. How do we start a problem investigation?">
            <div class="chip-label">🔍 Problem Management</div>
            Recurring API memory leak — how to open a problem?
          </div>
          <div class="prompt-chip" onclick="fillPrompt(this.dataset.msg)" data-msg="I need to provision access for a new developer joining on Monday — GitHub, AWS dev environment, and Jira.">
            <div class="chip-label">📋 Service Request</div>
            New developer onboarding access request
          </div>
          <div class="prompt-chip" onclick="fillPrompt(this.dataset.msg)" data-msg="Our P2 SLA compliance for this month is at 78%. What does that mean and what actions should we take?">
            <div class="chip-label">📊 SLA Monitoring</div>
            P2 SLA compliance is at 78% — what to do?
          </div>
        </div>
      </div>
    </div>

    <div class="input-bar">
      <textarea id="input" placeholder="Ask about incidents, changes, problems, service requests, or SLAs…" rows="1"></textarea>
      <button class="new-session-btn" onclick="newSession()" title="Start new conversation">↺ New</button>
      <button id="send-btn" onclick="send()">Send →</button>
    </div>
  </main>

</div>

<!-- Black Friday simulation overlay -->
<div class="sim-overlay hidden" id="sim-overlay" onclick="overlayClick(event)">
  <div class="sim-panel" id="sim-panel">

    <!-- Header -->
    <div class="sim-header">
      <div>
        <div class="sim-header-title">🛒 Black Friday Simulation</div>
        <div class="sim-header-sub" id="sim-header-sub">Preparing scenario…</div>
      </div>
      <div class="sim-progress-wrap">
        <div class="sim-progress-track">
          <div class="sim-progress-bar" id="sim-progress-bar"></div>
        </div>
        <div class="sim-step-counter" id="sim-step-counter"></div>
      </div>
      <button class="sim-close-btn" onclick="closeSimulation()">✕ Close</button>
    </div>

    <!-- Step timeline -->
    <div class="sim-body" id="sim-body"></div>

  </div>
</div>

<script>
const AGENTS = {agents_json};
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send-btn');
const welcome = document.getElementById('welcome');

// Session management
let sessionId = localStorage.getItem('sdc_session_id') || newSessionId();
updateSessionBadge();
renderAgentList(null);

// Auto-resize textarea
input.addEventListener('input', () => {{
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}});
input.addEventListener('keydown', e => {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
}});

function newSessionId() {{
  const id = crypto.randomUUID();
  localStorage.setItem('sdc_session_id', id);
  return id;
}}

function newSession() {{
  // Clear server-side session
  fetch(`/api/session/${{sessionId}}`, {{method: 'DELETE'}}).catch(() => {{}});
  sessionId = newSessionId();
  updateSessionBadge();
  chat.innerHTML = '';
  chat.appendChild(welcome);
  welcome.style.display = 'flex';
  welcome.style.flexDirection = 'column';
  welcome.style.alignItems = 'center';
  renderAgentList(null);
  document.getElementById('routing-badge').style.display = 'none';
  document.getElementById('orch-status').textContent = 'Ready';
}}

function updateSessionBadge() {{
  document.getElementById('session-badge').textContent = 'session: ' + sessionId.slice(0, 8) + '…';
}}

function renderAgentList(activeAgent) {{
  const list = document.getElementById('agent-list');
  list.innerHTML = AGENTS.map(a => `
    <div class="agent-card ${{a.id === activeAgent ? 'active' : ''}}" id="agent-card-${{a.id}}">
      <div class="agent-icon">${{a.icon}}</div>
      <div class="agent-name">${{a.name}}</div>
      <div class="agent-status">${{a.id === activeAgent ? '● Active' : 'Standby'}}</div>
    </div>
  `).join('');
}}

function fillPrompt(msg) {{
  input.value = msg;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  input.focus();
}}

function addMsg(role, html, meta) {{
  if (welcome && welcome.parentNode === chat) chat.removeChild(welcome);
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role;
  wrap.innerHTML = `<div class="msg-bubble">${{html}}</div><div class="msg-meta">${{meta ?? ''}}</div>`;
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return wrap;
}}

function escHtml(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function agentTag(agent, agentName, icon) {{
  return `<span class="agent-tag tag-${{agent}}">${{icon}} ${{agentName}}</span>`;
}}

async function send() {{
  const msg = input.value.trim();
  if (!msg || sendBtn.disabled) return;

  input.value = '';
  input.style.height = '44px';
  sendBtn.disabled = true;

  addMsg('user', escHtml(msg).replace(/\\n/g, '<br>'));
  const pending = addMsg('assistant', '<span class="thinking">Routing to specialist agent…</span>');

  // Show orchestrator as "routing"
  document.getElementById('orch-status').textContent = '⟳ Routing…';

  try {{
    const res = await fetch('/api/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ message: msg, session_id: sessionId }}),
    }});

    if (!res.ok) {{
      const err = await res.json().catch(() => ({{detail: 'Request failed'}}));
      pending.querySelector('.msg-bubble').innerHTML =
        `<span style="color:#f85149">⚠ Error: ${{escHtml(err.detail || 'Unknown error')}}</span>`;
      pending.querySelector('.msg-meta').textContent = '';
      return;
    }}

    const data = await res.json();

    // Update sidebar
    renderAgentList(data.agent);
    document.getElementById('orch-status').textContent = '✓ Routed';
    const rb = document.getElementById('routing-badge');
    rb.textContent = data.routing_reason ? '→ ' + data.routing_reason : '';
    rb.style.display = data.routing_reason ? 'inline-block' : 'none';

    // Render response
    const formatted = escHtml(data.response).replace(/\\n/g, '<br>');
    pending.querySelector('.msg-bubble').innerHTML = formatted;
    const meta = agentTag(data.agent, data.agent_name, data.agent_icon) +
      `<span>${{data.model}}</span>` +
      `<span>session: ${{data.session_id.slice(0,8)}}…</span>`;
    pending.querySelector('.msg-meta').innerHTML = meta;

  }} catch (err) {{
    pending.querySelector('.msg-bubble').innerHTML =
      `<span style="color:#f85149">⚠ Network error: ${{escHtml(err.message)}}</span>`;
    pending.querySelector('.msg-meta').textContent = '';
    document.getElementById('orch-status').textContent = 'Error';
  }} finally {{
    sendBtn.disabled = false;
    input.focus();
  }}
}}

// ── Black Friday Simulation ──────────────────────────────────────────────────

let simAbort = null;

function openSimulation() {{
  document.getElementById('sim-overlay').classList.remove('hidden');
  document.getElementById('sim-btn').disabled = true;
  document.getElementById('sim-body').innerHTML = '';
  document.getElementById('sim-progress-bar').style.width = '0%';
  document.getElementById('sim-step-counter').textContent = '';
  document.getElementById('sim-header-sub').textContent = 'Connecting to agent system…';
  simAbort = new AbortController();
  runSimulation(simAbort.signal);
}}

function closeSimulation() {{
  if (simAbort) {{ simAbort.abort(); simAbort = null; }}
  document.getElementById('sim-overlay').classList.add('hidden');
  document.getElementById('sim-btn').disabled = false;
}}

// Close when clicking the dark backdrop (not the panel itself)
function overlayClick(e) {{
  if (e.target === document.getElementById('sim-overlay')) closeSimulation();
}}

async function runSimulation(signal) {{
  const body    = document.getElementById('sim-body');
  const progBar = document.getElementById('sim-progress-bar');
  const counter = document.getElementById('sim-step-counter');
  const subhead = document.getElementById('sim-header-sub');

  try {{
    const resp = await fetch('/api/simulate/black-friday', {{
      method: 'POST',
      signal,
    }});

    if (!resp.ok) {{
      body.innerHTML = `<p style="color:#f85149">⚠ Server error ${{resp.status}}</p>`;
      document.getElementById('sim-btn').disabled = false;
      return;
    }}

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let   buf     = '';

    while (true) {{
      const {{ done, value }} = await reader.read();
      if (done) break;
      buf += decoder.decode(value, {{ stream: true }});

      // SSE lines arrive as "data: <json>\\n\\n" — process complete lines
      const lines = buf.split('\\n');
      buf = lines.pop();   // keep any incomplete trailing line

      for (const line of lines) {{
        if (!line.startsWith('data: ')) continue;
        let evt;
        try {{ evt = JSON.parse(line.slice(6)); }} catch {{ continue; }}
        handleSimEvent(evt, body, progBar, counter, subhead);
      }}
    }}

  }} catch (err) {{
    if (err.name === 'AbortError') return;   // user closed the panel
    const el = document.createElement('p');
    el.style.color = '#f85149';
    el.textContent = '⚠ Simulation failed: ' + err.message;
    body.appendChild(el);
    document.getElementById('sim-btn').disabled = false;
  }}
}}

function handleSimEvent(evt, body, progBar, counter, subhead) {{
  if (evt.type === 'step_start') {{
    const pct = ((evt.step - 1) / evt.total * 100).toFixed(1);
    progBar.style.width = pct + '%';
    counter.textContent = `Step ${{evt.step}} of ${{evt.total}}`;
    subhead.textContent = evt.description;

    const stepEl = document.createElement('div');
    stepEl.className = 'sim-step';
    stepEl.id = `sim-step-${{evt.step}}`;
    stepEl.innerHTML =
      `<div class="sim-step-header">` +
        `<span class="sim-step-num running" id="sim-num-${{evt.step}}">${{evt.step}}</span>` +
        `<span class="sim-step-desc">${{escHtml(evt.description)}}</span>` +
      `</div>` +
      `<div class="sim-query-bubble">${{escHtml(evt.query).replace(/\\n/g,'<br>')}}</div>` +
      `<div class="sim-response-bubble thinking" id="sim-resp-${{evt.step}}">Agent is thinking…</div>`;
    body.appendChild(stepEl);
    body.scrollTop = body.scrollHeight;
  }}

  if (evt.type === 'step_end') {{
    const pct = (evt.step / evt.total * 100).toFixed(1);
    progBar.style.width = pct + '%';
    counter.textContent = `Step ${{evt.step}} of ${{evt.total}} complete`;

    const numEl  = document.getElementById(`sim-num-${{evt.step}}`);
    const respEl = document.getElementById(`sim-resp-${{evt.step}}`);

    if (numEl) {{
      numEl.className  = 'sim-step-num done';
      numEl.textContent = '✓';
    }}
    if (respEl) {{
      respEl.classList.remove('thinking');
      respEl.textContent = evt.response;

      const meta = document.createElement('div');
      meta.className = 'sim-response-meta';
      meta.innerHTML =
        agentTag(evt.agent, evt.agent_name, evt.agent_icon) +
        `<span>${{evt.latency_ms.toLocaleString()}} ms</span>` +
        (evt.routing_reason ? `<span style="color:var(--muted);font-style:italic">${{escHtml(evt.routing_reason)}}</span>` : '');
      respEl.after(meta);
    }}

    // Mirror active agent in sidebar
    renderAgentList(evt.agent);
    body.scrollTop = body.scrollHeight;
  }}

  if (evt.type === 'error') {{
    const numEl  = document.getElementById(`sim-num-${{evt.step}}`);
    const respEl = document.getElementById(`sim-resp-${{evt.step}}`);
    if (numEl)  {{ numEl.className = 'sim-step-num errored'; numEl.textContent = '✗'; }}
    if (respEl) {{
      respEl.classList.remove('thinking');
      respEl.style.color = '#f85149';
      respEl.textContent = '⚠ ' + evt.error;
    }}
    body.scrollTop = body.scrollHeight;
  }}

  if (evt.type === 'sim_complete') {{
    progBar.style.width = '100%';
    counter.textContent = `All ${{evt.total_steps}} steps complete`;
    subhead.textContent  = 'Simulation finished';

    const banner = document.createElement('div');
    banner.className = 'sim-done-banner';
    banner.innerHTML =
      `✅ Black Friday simulation complete — ${{evt.total_steps}} queries processed across all agents` +
      `<small>All spans, metrics and logs exported to Dash0 · Session cleaned up</small>`;
    body.appendChild(banner);
    body.scrollTop = body.scrollHeight;
    document.getElementById('sim-btn').disabled = false;
    renderAgentList(null);
    document.getElementById('orch-status').textContent = 'Ready';
  }}
}}

// ── Chaos panel ──────────────────────────────────────────────────────────────

const CHAOS_MODES = [
  {{ id: 'none',         label: '✅ None (normal)',       hasOptions: false }},
  {{ id: 'llm_slow',    label: '🐢 LLM Slow',             hasOptions: true  }},
  {{ id: 'llm_error',   label: '💥 LLM Error',            hasOptions: true  }},
  {{ id: 'tool_error',  label: '🔧 Tool Error',            hasOptions: true  }},
  {{ id: 'rag_degraded',label: '🕳  RAG Degraded',         hasOptions: false }},
];

let chaosOpen = false;
let currentChaosMode = 'none';

function toggleChaosPanel() {{
  chaosOpen = !chaosOpen;
  document.getElementById('chaos-panel').classList.toggle('hidden', !chaosOpen);
  if (chaosOpen) renderChaosModes();
}}

function renderChaosModes() {{
  const container = document.getElementById('chaos-modes');
  container.innerHTML = CHAOS_MODES.map(m =>
    `<button class="chaos-mode-btn ${{m.id}} ${{currentChaosMode === m.id ? 'active' : ''}}"
       onclick="selectChaosMode('${{m.id}}', ${{m.hasOptions}})">${{m.label}}</button>`
  ).join('');
}}

function selectChaosMode(mode, hasOptions) {{
  document.getElementById('chaos-options').style.display = hasOptions ? 'flex' : 'none';
  document.querySelectorAll('.chaos-mode-btn').forEach(b =>
    b.classList.toggle('active', b.classList.contains(mode))
  );
  applyChaos(mode);
}}

async function applyChaos(mode) {{
  const prob  = parseInt(document.getElementById('chaos-prob')?.value  ?? 50) / 100;
  const delay = parseInt(document.getElementById('chaos-delay')?.value ?? 3000);
  try {{
    let res;
    if (mode === 'none') {{
      res = await fetch('/api/chaos', {{ method: 'DELETE' }});
    }} else {{
      res = await fetch('/api/chaos', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ mode, probability: prob, delay_ms: delay }}),
      }});
    }}
    const data = await res.json();
    currentChaosMode = data.mode;
    renderChaosModes();

    const btn    = document.getElementById('chaos-btn');
    const status = document.getElementById('chaos-status');
    if (data.active) {{
      btn.classList.add('active');
      btn.textContent = `🔥 Chaos: ${{data.mode}}`;
      status.className = 'chaos-status on';
      status.textContent = `Active: ${{data.description}} — spans will appear in Dash0 as chaos.* errors`;
    }} else {{
      btn.classList.remove('active');
      btn.textContent = '🔥 Chaos';
      status.className = 'chaos-status';
      status.textContent = 'Off — normal operation';
    }}
  }} catch(e) {{
    document.getElementById('chaos-status').textContent = 'Error: ' + e.message;
  }}
}}

// Wire up probability slider display
document.addEventListener('DOMContentLoaded', () => {{
  const slider = document.getElementById('chaos-prob');
  const label  = document.getElementById('chaos-prob-val');
  if (slider) slider.addEventListener('input', () => {{ label.textContent = slider.value + '%'; }});
}});
</script>
</body>
</html>"""
