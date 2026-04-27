"""LangGraph graph: orchestrator → specialist agent → tools loop → END.

Topology per agent:

    orchestrator
         │  (conditional: current_agent)
         ▼
    [incident | change | problem | service | sla]
         │
    tools_condition (from langgraph.prebuilt)
         │                    │
    has tool_calls?        no tool calls
         │                    │
         ▼                    ▼
  {agent}_tools             END
         │
         ▼ (loop back)
    [same agent node]
         │
        ...
         ▼
        END

Each specialist agent runs a full ReAct loop — the LLM reasons, calls tools
as needed (RAG search, domain calculations), receives results, and produces
a final answer before exiting to END.
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition

from .state import SDCState
from .agents.orchestrator import orchestrate_node
from .agents.incident import incident_node
from .agents.change import change_node
from .agents.problem import problem_node
from .agents.service import service_node
from .agents.sla import sla_node
from .agents.tracing import make_instrumented_tool_node


def _route(state: SDCState) -> str:
    """Route from orchestrator to the correct specialist node."""
    return state.get("current_agent", "incident")


def build_graph() -> object:
    # Import tool lists (agents cache them via lru_cache — same instances used
    # both in the agent nodes and in the ToolNode executors)
    from sdc.tools.incident_tools import get_incident_tools
    from sdc.tools.change_tools import get_change_tools
    from sdc.tools.problem_tools import get_problem_tools
    from sdc.tools.service_tools import get_service_tools
    from sdc.tools.sla_tools import get_sla_tools

    g = StateGraph(SDCState)

    # ── Orchestrator ────────────────────────────────────────────────────────
    g.add_node("orchestrator", orchestrate_node)

    # ── Specialist agent nodes ───────────────────────────────────────────────
    g.add_node("incident", incident_node)
    g.add_node("change",   change_node)
    g.add_node("problem",  problem_node)
    g.add_node("service",  service_node)
    g.add_node("sla",      sla_node)

    # ── Tool executor nodes (one per agent) ──────────────────────────────────
    # make_instrumented_tool_node wraps ToolNode in an sdc.graph.node OTel span
    # so that tool.invoke child spans nest under it in the Dash0 trace tree.
    # ToolNode automatically:
    #   • reads tool_calls from the last AIMessage
    #   • executes each tool
    #   • appends ToolMessage results back into state["messages"]
    g.add_node("incident_tools", make_instrumented_tool_node(get_incident_tools(), "incident_tools"))
    g.add_node("change_tools",   make_instrumented_tool_node(get_change_tools(),   "change_tools"))
    g.add_node("problem_tools",  make_instrumented_tool_node(get_problem_tools(),  "problem_tools"))
    g.add_node("service_tools",  make_instrumented_tool_node(get_service_tools(),  "service_tools"))
    g.add_node("sla_tools",      make_instrumented_tool_node(get_sla_tools(),      "sla_tools"))

    # ── Entry point ──────────────────────────────────────────────────────────
    g.set_entry_point("orchestrator")

    # ── Orchestrator → specialist (based on current_agent in state) ──────────
    g.add_conditional_edges(
        "orchestrator",
        _route,
        {
            "incident": "incident",
            "change":   "change",
            "problem":  "problem",
            "service":  "service",
            "sla":      "sla",
        },
    )

    # ── ReAct loop per agent ─────────────────────────────────────────────────
    # tools_condition returns "tools" if last message has tool_calls, else END.
    # We map "tools" → the agent-specific ToolNode so each loop stays isolated.
    # After tools execute, loop back to the same agent for the next reasoning step.
    for agent in ("incident", "change", "problem", "service", "sla"):
        g.add_conditional_edges(
            agent,
            tools_condition,
            {
                "tools": f"{agent}_tools",
                END: END,
            },
        )
        g.add_edge(f"{agent}_tools", agent)

    return g.compile()


# Module-level singleton — compiled once at import time
sdc_graph = build_graph()
