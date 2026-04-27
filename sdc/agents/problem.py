"""Problem Management Agent — tool-calling ReAct node.

Tools:
  • search_runbook              — look up SDC problem management procedures
  • search_historical_records   — find past problem records, KEDB entries, RCA outcomes
  • check_problem_trigger       — determine if a problem record is warranted
  • suggest_rca_method          — recommend the right RCA technique
  • format_kedb_entry           — generate a correctly structured KEDB entry
"""

from functools import lru_cache
from langchain_core.messages import AIMessage, SystemMessage

from ..state import SDCState
from .base_llm import make_llm
from .tracing import graph_node_span

SYSTEM_PROMPT = """You are the **Problem Management Agent** for SDC (Service Delivery Company), \
an ITIL-aligned expert in root cause analysis, Known Error management, and recurring incident prevention.

You have access to tools — use them for thorough, evidence-based problem management:
- **search_runbook**: Find official SDC problem management procedures, KEDB format, RCA templates.
- **search_historical_records**: Look up past problem records, KEDB entries, and RCA outcomes.
- **check_problem_trigger**: Determine whether a pattern meets the threshold for a problem record.
- **suggest_rca_method**: Choose the right RCA technique for the problem characteristics.
- **format_kedb_entry**: Generate a correctly structured KEDB entry ready for the database.

**When to use tools:**
- Always check problem trigger thresholds when someone reports recurring incidents.
- Search historical records first — the root cause may already be in the KEDB.
- Use suggest_rca_method before starting any investigation to pick the right approach.
- Use format_kedb_entry once root cause is confirmed to create the KEDB entry.

**Problem lifecycle:**
1. Trigger → 2. Log PRB → 3. Prioritise → 4. Investigate (RCA) → 5. Workaround (KEDB)
→ 6. Known Error declaration → 7. RFC for permanent fix → 8. Verify fix → 9. Close

Always ask for: linked incident IDs, affected services, first occurrence date, and any suspected cause."""


@lru_cache(maxsize=1)
def _get_tools():
    from sdc.tools.problem_tools import get_problem_tools
    return get_problem_tools()


@graph_node_span("problem")
def problem_node(state: SDCState) -> dict:
    tools = _get_tools()
    llm = make_llm("problem").bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    if not (hasattr(response, "tool_calls") and response.tool_calls):
        response = AIMessage(
            content=response.content or "",
            name="problem",
            additional_kwargs=response.additional_kwargs or {},
        )
    return {"messages": [response]}
