"""Incident Response Agent — tool-calling ReAct node.

The LLM is given 5 tools and decides which to call:
  • search_runbook              — look up SDC incident procedures
  • search_historical_records   — find past incidents matching the scenario
  • classify_priority           — determine P1–P4 from impact parameters
  • calculate_resolution_deadline — compute SLA deadline from start time
  • get_escalation_path         — get contacts + cadence for a priority level

The agent node participates in a ReAct loop:
  incident → tools_condition → incident_tools → incident → ... → END
"""

from functools import lru_cache
from langchain_core.messages import AIMessage, SystemMessage

from ..state import SDCState
from .base_llm import make_llm
from .tracing import graph_node_span

SYSTEM_PROMPT = """You are the **Incident Response Agent** for SDC (Service Delivery Company), \
an ITIL-aligned expert in incident classification, escalation, and resolution coordination.

You have access to tools — use them to give accurate, grounded answers:
- **search_runbook**: Find the official SDC incident management procedure.
- **search_historical_records**: Look up past SDC incidents similar to the current situation.
- **classify_priority**: Determine the correct P1–P4 priority from impact data.
- **calculate_resolution_deadline**: Compute the exact SLA deadline for an incident.
- **get_escalation_path**: Get the full escalation chain and communication cadence.

**When to use tools:**
- Always search historical records when asked about past incidents or patterns.
- Use classify_priority whenever priority is unclear or needs confirmation.
- Use calculate_resolution_deadline when a start time is provided.
- Search the runbook for procedural questions (escalation templates, post-mortem triggers, etc.).

**Core priority thresholds:**
- P1: Complete outage / revenue impact / >500 users / no workaround → 1-hour SLA
- P2: Major degradation / >100 users / no workaround → 4-hour SLA
- P3: Partial impact / workaround available / <100 users → 8 business hours
- P4: Minimal / cosmetic / single user → 3 business days

Be direct and action-oriented. Always state the priority, SLA deadline, and first three actions."""


@lru_cache(maxsize=1)
def _get_tools():
    from sdc.tools.incident_tools import get_incident_tools
    return get_incident_tools()


@graph_node_span("incident")
def incident_node(state: SDCState) -> dict:
    tools = _get_tools()
    llm = make_llm("incident").bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    # Tag final text responses with agent name for the UI
    if not (hasattr(response, "tool_calls") and response.tool_calls):
        response = AIMessage(
            content=response.content or "",
            name="incident",
            additional_kwargs=response.additional_kwargs or {},
        )
    return {"messages": [response]}
