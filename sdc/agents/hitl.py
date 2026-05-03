"""Human-in-the-loop checkpoints — one per specialist agent.

Each specialist runs its full ReAct loop (think → tool → think → … → final
answer) without interruption.  The hitl_review node then sits between the
agent's final answer and END.  When state["hitl_enabled"] is True, the node
calls langgraph.types.interrupt(...) with an agent-specific approval prompt;
the graph pauses, the FastAPI handler surfaces the prompt to the UI, and the
operator's choice is fed back via Command(resume=value).

When state["hitl_enabled"] is False (the default), the node is a no-op
pass-through — the graph behaves exactly as it did before HITL existed.

Per-agent checkpoint design (the "whatever makes most sense" call):

  incident → "Confirm priority + runbook"  — choose which runbook to follow
  change   → "CAB-style approval"          — approve / reject the RFC
  problem  → "Choose RCA method"           — 5-Whys / Fishbone / KT / FTA
  service  → "Approve access provisioning" — security checkpoint
  sla      → "Trigger SLA escalation"      — page on-call or hold

All five checkpoints share the same approve/reject/options shape so the UI
only needs to render a single component.  An agent-specific `options` list
plus optional `runbooks` list lets each agent surface its own decision
context (e.g. SLA's "hold the escalation" vs Problem's "pick RCA method").
"""
from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from ..state import SDCState

# Each entry: (title, prompt, options).  Options are the choices the operator
# can pick — the HITL node compares the resume value (case-insensitive) to
# decide whether to pass through or amend the agent's answer.
HITL_PROMPTS: dict[str, dict] = {
    "incident": {
        "title":   "Incident response — confirm priority and runbook",
        "prompt":  "The Incident Response Agent has classified this incident and proposed a course of action. Approve to proceed, reject to halt, or pick a different runbook.",
        "options": ["approve", "reject"],
        "runbooks": [
            "RB-INC-001 P1 outage runbook",
            "RB-INC-002 P2 degraded service runbook",
            "RB-INC-003 P3 isolated incident runbook",
        ],
    },
    "change": {
        "title":   "Change Advisory Board — approve change?",
        "prompt":  "Acting as the CAB chair: approve, reject, or send back for modification. Emergency changes still require retrospective RFC within 24h.",
        "options": ["approve", "reject"],
    },
    "problem": {
        "title":   "Problem management — pick RCA method",
        "prompt":  "Approve the agent's proposed root-cause-analysis approach, or pick a different method.",
        "options": ["approve", "5-Whys", "Fishbone", "Kepner-Tregoe", "Fault-Tree"],
    },
    "service": {
        "title":   "Service request — approve access provisioning",
        "prompt":  "Security checkpoint: approve the proposed access grant or reject and require re-review.",
        "options": ["approve", "reject"],
    },
    "sla": {
        "title":   "SLA monitoring — trigger escalation?",
        "prompt":  "An SLA breach has been detected. Approve to page the on-call escalation chain, hold to defer until the next review window, or reject to dismiss.",
        "options": ["approve", "hold", "reject"],
    },
}

# Default for any agent that doesn't have a specific entry (e.g. orchestrator,
# general fallback).  Should never fire in practice — the graph wires HITL
# only after the five specialists.
_FALLBACK = {
    "title":   "Operator confirmation",
    "prompt":  "Approve the agent's proposed action?",
    "options": ["approve", "reject"],
}


def _last_ai_text(state: SDCState, max_chars: int = 1200) -> str:
    """Return the agent's most recent final answer text — used as context in the prompt."""
    for m in reversed(state.get("messages") or []):
        if getattr(m, "type", None) == "ai" and (m.content or "").strip():
            return (m.content or "")[:max_chars]
    return ""


def hitl_review_node(state: SDCState) -> dict:
    """The shared review checkpoint.  Pauses if HITL is enabled, otherwise no-op.

    On resume, the value passed to Command(resume=...) is interpreted:
        - "approve"           → state passes through (agent's answer stands)
        - "reject"            → an AIMessage is appended saying the operator rejected
        - any other string    → recorded as the chosen option / runbook / RCA method
                                and an annotation message is appended so the agent's
                                final reply makes the operator's choice visible
    """
    if not state.get("hitl_enabled"):
        return {}

    agent_id = state.get("current_agent") or "general"
    cfg = HITL_PROMPTS.get(agent_id, _FALLBACK)
    proposal_excerpt = _last_ai_text(state)

    # interrupt() pauses the graph and surfaces this payload to the calling
    # ainvoke().  The FastAPI handler picks it up and returns it to the UI.
    decision = interrupt({
        "type":     "hitl",
        "agent":    agent_id,
        "title":    cfg["title"],
        "prompt":   cfg["prompt"],
        "options":  cfg.get("options") or ["approve", "reject"],
        "runbooks": cfg.get("runbooks") or [],
        "proposal_excerpt": proposal_excerpt,
    })

    # Normalise the resume value
    if decision is None:
        decision = "approve"
    decision_str = str(decision).strip()
    decision_lc  = decision_str.lower()

    if decision_lc == "reject":
        return {
            "hitl_decision": "rejected",
            "messages": [AIMessage(
                content=f"**Action halted by operator.** The {agent_id} agent's proposed action has been rejected pending operator override.",
                additional_kwargs={"hitl_decision": "rejected", "agent": agent_id},
            )],
        }

    if decision_lc == "approve":
        return {"hitl_decision": "approved"}

    # Operator picked a non-default option (e.g. "5-Whys", "RB-INC-002 …", "hold").
    # Append an annotation so the chosen branch is visible in the conversation.
    return {
        "hitl_decision": f"approved:{decision_str}",
        "messages": [AIMessage(
            content=f"**Operator selected:** {decision_str}\n\nThe {agent_id} agent will use this choice.",
            additional_kwargs={"hitl_decision": decision_str, "agent": agent_id},
        )],
    }
