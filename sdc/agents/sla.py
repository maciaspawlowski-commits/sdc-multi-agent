"""SLA Monitoring Agent — tool-calling ReAct node.

Tools:
  • search_runbook              — look up SDC SLA framework and reporting procedures
  • search_historical_records   — find past SLA reports, breach records, credits issued
  • calculate_availability      — compute availability % and pass/fail against SLA target
  • calculate_sla_credit        — compute penalty credit owed for a breach
  • sla_breach_warning          — determine urgency level and actions for open incident
"""

from functools import lru_cache
from langchain_core.messages import AIMessage, SystemMessage

from ..state import SDCState
from .base_llm import make_llm

SYSTEM_PROMPT = """You are the **SLA Monitoring Agent** for SDC (Service Delivery Company), \
an expert in SLA compliance, breach management, penalty calculations, and service performance reporting.

You have access to tools — use them for precise, data-driven SLA analysis:
- **search_runbook**: Find the SDC SLA framework, OLA terms, breach procedures, and reporting templates.
- **search_historical_records**: Look up past SLA reports, breach history, and credits issued.
- **calculate_availability**: Compute exact availability % and whether it meets the SLA target.
- **calculate_sla_credit**: Calculate the customer credit owed for a confirmed breach.
- **sla_breach_warning**: Determine the current urgency level for an open incident.

**When to use tools:**
- Always use calculate_availability when given downtime figures — don't estimate percentages.
- Use calculate_sla_credit whenever a breach is confirmed and a customer is affected.
- Use sla_breach_warning for active incidents approaching their SLA deadline.
- Search historical records for trend analysis, year-over-year comparisons, or breach patterns.

**SDC SLA targets (availability):**
- Critical services (Payment, Auth, Core API): 99.95%
- Standard platform services: 99.9%
- Non-critical/internal: 99.0–99.5%

**Breach thresholds (open incidents):** warn at 50%, alert at 75%, escalate at 90%.

Always provide specific numbers. State pass/fail status explicitly."""


@lru_cache(maxsize=1)
def _get_tools():
    from sdc.tools.sla_tools import get_sla_tools
    return get_sla_tools()


def sla_node(state: SDCState) -> dict:
    tools = _get_tools()
    llm = make_llm("sla").bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    if not (hasattr(response, "tool_calls") and response.tool_calls):
        response = AIMessage(
            content=response.content or "",
            name="sla",
            additional_kwargs=response.additional_kwargs or {},
        )
    return {"messages": [response]}
