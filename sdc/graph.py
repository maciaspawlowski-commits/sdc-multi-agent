"""LangGraph graph: orchestrator → one of 5 specialist SDC agents."""

from langgraph.graph import StateGraph, END
from .state import SDCState
from .agents.orchestrator import orchestrate_node
from .agents.incident import incident_node
from .agents.change import change_node
from .agents.problem import problem_node
from .agents.service import service_node
from .agents.sla import sla_node


def _route(state: SDCState) -> str:
    return state.get("current_agent", "incident")


def build_graph():
    g = StateGraph(SDCState)

    g.add_node("orchestrator", orchestrate_node)
    g.add_node("incident", incident_node)
    g.add_node("change", change_node)
    g.add_node("problem", problem_node)
    g.add_node("service", service_node)
    g.add_node("sla", sla_node)

    g.set_entry_point("orchestrator")

    g.add_conditional_edges(
        "orchestrator",
        _route,
        {
            "incident": "incident",
            "change": "change",
            "problem": "problem",
            "service": "service",
            "sla": "sla",
        },
    )

    g.add_edge("incident", END)
    g.add_edge("change", END)
    g.add_edge("problem", END)
    g.add_edge("service", END)
    g.add_edge("sla", END)

    return g.compile()


# Module-level singleton — compiled once at import time
sdc_graph = build_graph()
