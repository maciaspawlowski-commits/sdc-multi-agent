"""RAG search tools — one pair per agent, agent_key baked in via closure.

Each agent gets its own `search_runbook` and `search_historical_records`
tool pointing at its own Chroma collections. The LLM decides when and
what to search; retrieval is no longer eager/automatic.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def make_rag_tools(agent_key: str) -> list:
    """Return [search_runbook, search_historical_records] for the given agent."""

    @tool
    def search_runbook(query: str) -> str:
        """Search the SDC procedural runbook for official process guidance,
        step-by-step procedures, templates, policies, SLA targets, escalation
        paths, and best practices. Use this when you need to know the correct
        procedure for handling a situation — e.g. 'how do I classify a P1?',
        'what is the emergency change process?', 'what does a KEDB entry
        contain?'. Returns the most relevant runbook sections."""
        logger.info(
            "sdc.rag.query agent=%s collection=runbook query=%.150s",
            agent_key, query.replace("\n", " "),
        )
        from sdc.vectorstore import retrieve
        result = retrieve(agent_key, query, k=3)
        found = bool(result)
        logger.info(
            "sdc.rag.result agent=%s collection=runbook found=%s result_len=%d",
            agent_key, found, len(result) if result else 0,
        )
        return result if result else "No relevant runbook sections found for that query."

    @tool
    def search_historical_records(query: str) -> str:
        """Search SDC's historical operational records — past incidents (INC),
        changes (CHG), problem records (PRB), service requests (SR), and SLA
        reports. Use this to find precedents, previous root causes, similar past
        failures, historical resolution approaches, or compliance history.
        Examples: 'past payment gateway outages', 'previous database disk full
        incidents', 'change rollbacks in 2024', 'SLA breaches in Q3'.
        Returns the most relevant historical records."""
        logger.info(
            "sdc.rag.query agent=%s collection=records query=%.150s",
            agent_key, query.replace("\n", " "),
        )
        from sdc.vectorstore import retrieve_records
        result = retrieve_records(agent_key, query, k=3)
        found = bool(result)
        logger.info(
            "sdc.rag.result agent=%s collection=records found=%s result_len=%d",
            agent_key, found, len(result) if result else 0,
        )
        return result if result else "No matching historical records found for that query."

    # Set readable names for observability / LangSmith traces
    search_runbook.name = f"search_runbook_{agent_key}"
    search_historical_records.name = f"search_historical_records_{agent_key}"

    return [search_runbook, search_historical_records]
