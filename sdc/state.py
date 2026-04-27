from typing import Annotated, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

AGENT_NAMES = {
    "incident": "Incident Response Agent",
    "change": "Change Management Agent",
    "problem": "Problem Management Agent",
    "service": "Service Request Agent",
    "sla": "SLA Monitoring Agent",
    "general": "General Assistant",
}

AGENT_ICONS = {
    "incident": "🚨",
    "change": "🔄",
    "problem": "🔍",
    "service": "📋",
    "sla": "📊",
    "general": "💬",
}


class SDCState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_agent: Optional[str]   # "incident"|"change"|"problem"|"service"|"sla"|"general"
    routing_reason: Optional[str]  # why this agent was selected
