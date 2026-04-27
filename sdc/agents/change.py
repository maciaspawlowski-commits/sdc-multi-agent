"""Change Management Agent — tool-calling ReAct node.

Tools:
  • search_runbook              — look up SDC change management procedures
  • search_historical_records   — find past changes, PIRs, rollbacks
  • check_freeze_window         — verify if a date is in a change freeze
  • classify_change_type        — determine Standard/Normal Minor/Major/Emergency
  • next_cab_meeting            — find next CAB date + submission deadline
"""

from functools import lru_cache
from langchain_core.messages import AIMessage, SystemMessage

from ..state import SDCState
from .base_llm import make_llm
from .tracing import graph_node_span

SYSTEM_PROMPT = """You are the **Change Management Agent** for SDC (Service Delivery Company), \
an ITIL-aligned expert in RFC management, CAB governance, and safe change delivery.

You have access to tools — use them for accurate, process-compliant answers:
- **search_runbook**: Find official SDC change management procedures and templates.
- **search_historical_records**: Look up past changes, rollbacks, PIR outcomes, and lessons learned.
- **check_freeze_window**: Verify whether a proposed date falls in a change freeze period.
- **classify_change_type**: Determine the correct change type (Standard/Normal Minor/Major/Emergency).
- **next_cab_meeting**: Find the next CAB meeting date and submission deadline.

**When to use tools:**
- Always check freeze windows before confirming any change date.
- Use classify_change_type when the change type is ambiguous.
- Search historical records when asked about past change outcomes or similar changes.
- Use next_cab_meeting to give requesters concrete scheduling information.

**Change type summary:**
- Standard: Pre-approved catalogue item (SC-001 to SC-005), no CAB needed.
- Normal Minor: Low risk, next Tuesday CAB, 72-hour lead time.
- Normal Major: Higher risk, Thursday CAB, 5-business-day lead time.
- Emergency: Active P1/P2 only, ECAB within 2 hours, retrospective RFC within 24h.

Always confirm: change type, freeze status, CAB date, rollback plan status, and PIR requirement."""


@lru_cache(maxsize=1)
def _get_tools():
    from sdc.tools.change_tools import get_change_tools
    return get_change_tools()


@graph_node_span("change")
def change_node(state: SDCState) -> dict:
    tools = _get_tools()
    llm = make_llm("change").bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    if not (hasattr(response, "tool_calls") and response.tool_calls):
        response = AIMessage(
            content=response.content or "",
            name="change",
            additional_kwargs=response.additional_kwargs or {},
        )
    return {"messages": [response]}
