"""Orchestrator agent — classifies the user intent and routes to the right specialist."""

import json
import logging
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from ..state import SDCState
from .base_llm import make_llm

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are the SDC (Service Delivery Company) intelligent routing assistant.
Your ONLY job is to read the user's message and classify it into one of these categories:

- "incident"  → outages, errors, service down, degraded performance, alerts, P1/P2/P3/P4
- "change"    → deployments, releases, change requests, RFC, CAB, rollbacks, maintenance windows
- "problem"   → root cause analysis, recurring issues, RCA, KEDB, known errors, post-mortems
- "service"   → new accounts, access requests, software provisioning, onboarding, offboarding, hardware
- "sla"       → SLA reports, breach queries, MTTR/MTTA metrics, compliance percentages, availability

Respond with ONLY valid JSON in this exact format, nothing else:
{"agent": "<category>", "reason": "<one sentence explaining why>"}"""


def orchestrate_node(state: SDCState) -> dict:
    """Classify the latest user message and set current_agent in state."""
    try:
        from sdc_otel import SDCOTelCallback
        callbacks = [SDCOTelCallback(agent_key="orchestrator")]
    except Exception:
        callbacks = []

    import os
    llm = ChatOllama(
        model=os.getenv("LLM_MODEL", "llama3.2"),
        temperature=0,
        format="json",
        callbacks=callbacks,
    )

    last_human = _last_human_message(state)
    messages = [
        SystemMessage(content=CLASSIFICATION_PROMPT),
        {"role": "user", "content": last_human},
    ]

    try:
        response = llm.invoke(messages)
        parsed = json.loads(response.content)
        agent = parsed.get("agent", "incident")
        reason = parsed.get("reason", "")
    except Exception as exc:
        logger.warning("Orchestrator parse failed (%s) — falling back to keyword routing", exc)
        agent, reason = _keyword_fallback(last_human)

    agent = agent if agent in ("incident", "change", "problem", "service", "sla") else "incident"
    logger.info("Orchestrator routed to '%s': %s", agent, reason)

    return {"current_agent": agent, "routing_reason": reason}


def _last_human_message(state: SDCState) -> str:
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _keyword_fallback(text: str) -> tuple[str, str]:
    """Simple keyword routing when JSON parsing fails."""
    t = text.lower()
    if any(w in t for w in ["outage", "down", "incident", "alert", "error", "p1", "p2", "p3", "p4", "degraded", "broken"]):
        return "incident", "Keyword match: incident-related terms detected"
    if any(w in t for w in ["deploy", "release", "change", "rfc", "cab", "rollback", "maintenance", "patch"]):
        return "change", "Keyword match: change management terms detected"
    if any(w in t for w in ["root cause", "rca", "problem", "recurring", "kedb", "known error", "post-mortem", "pareto"]):
        return "problem", "Keyword match: problem management terms detected"
    if any(w in t for w in ["access", "account", "provision", "onboard", "offboard", "software", "hardware", "license", "request"]):
        return "service", "Keyword match: service request terms detected"
    if any(w in t for w in ["sla", "slo", "breach", "mttr", "mtta", "compliance", "availability", "report", "metric"]):
        return "sla", "Keyword match: SLA monitoring terms detected"
    return "incident", "Default routing to incident response"
