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
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from langchain_core.messages import HumanMessage
from opentelemetry import metrics, trace
from pydantic import BaseModel

from sdc.graph import sdc_graph
from sdc.state import AGENT_ICONS, AGENT_NAMES

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")

# OTel instruments — populated in lifespan
_tracer: Optional[trace.Tracer] = None
_agent_counter: Optional[metrics.Counter] = None
_latency_hist: Optional[metrics.Histogram] = None
_error_counter: Optional[metrics.Counter] = None


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

    logger.info(
        "SDC Multi-Agent System ready — http://localhost:8000  (model: %s @ %s)",
        LLM_MODEL, OLLAMA_HOST,
    )
    yield
    logger.info("SDC Multi-Agent System shutting down")


app = FastAPI(title="SDC Multi-Agent System", lifespan=lifespan)

# ── In-memory conversation sessions ─────────────────────────────────────────
# Maps session_id → list of LangChain messages (the conversation history)
_sessions: dict[str, list] = {}


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
    }


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
        history = _sessions.get(session_id, [])
        history.append(HumanMessage(content=req.message))

        initial_state = {
            "messages": history,
            "current_agent": None,
            "routing_reason": None,
        }

        try:
            result = await sdc_graph.ainvoke(initial_state)
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            span.record_exception(exc)
            span.set_attribute("error.type", type(exc).__name__)
            _error_counter.add(1, {"sdc.agent": "unknown", "llm.model": LLM_MODEL})
            _latency_hist.record(latency_ms, {"sdc.agent": "unknown", "status": "error"})
            logger.error("Graph invocation failed session=%s error=%s", session_id, exc)
            raise HTTPException(status_code=502, detail=f"Agent error: {exc}")

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
        _sessions[session_id] = list(result["messages"])

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
def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"cleared": session_id}


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
</script>
</body>
</html>"""
