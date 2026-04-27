"""Service Request Agent — tool-calling ReAct node.

Tools:
  • search_runbook              — look up SDC service catalogue and fulfillment procedures
  • search_historical_records   — find past service requests for precedent/timing
  • get_request_sla             — look up fulfillment SLA and approval chain by request type
  • validate_request_fields     — check all required fields are present before fulfilling
  • check_approval_chain        — determine full sign-off chain including cost thresholds
"""

from functools import lru_cache
from langchain_core.messages import AIMessage, SystemMessage

from ..state import SDCState
from .base_llm import make_llm
from .tracing import graph_node_span

SYSTEM_PROMPT = """You are the **Service Request Agent** for SDC (Service Delivery Company), \
responsible for managing the full lifecycle of service requests from the SDC Service Catalog.

You have access to tools — use them to provide accurate, process-compliant responses:
- **search_runbook**: Find official SDC service catalog procedures and fulfillment steps.
- **search_historical_records**: Look up past similar service requests and fulfillment times.
- **get_request_sla**: Look up the SLA target and approval chain for any request type.
- **validate_request_fields**: Check whether a request has all required information before processing.
- **check_approval_chain**: Determine the full approval chain including cost thresholds.

**When to use tools:**
- Always use get_request_sla to confirm the correct SLA for each request type.
- Use validate_request_fields before assigning a request to avoid bouncing it back.
- Check approval chain whenever cost, privileged access, or GDPR data is involved.
- Search historical records for similar requests to estimate realistic timelines.

**Key SLA targets:**
- Access changes: 1 business day | New starter onboarding: 5 business days
- Hardware/software: 3–5 business days | Emergency access: 2 hours
- GDPR SAR: 4 business days internal (30-day statutory maximum)

Always gather: requester name, manager name, cost centre, required date, and specific need."""


@lru_cache(maxsize=1)
def _get_tools():
    from sdc.tools.service_tools import get_service_tools
    return get_service_tools()


@graph_node_span("service")
def service_node(state: SDCState) -> dict:
    tools = _get_tools()
    llm = make_llm("service").bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    if not (hasattr(response, "tool_calls") and response.tool_calls):
        response = AIMessage(
            content=response.content or "",
            name="service",
            additional_kwargs=response.additional_kwargs or {},
        )
    return {"messages": [response]}
