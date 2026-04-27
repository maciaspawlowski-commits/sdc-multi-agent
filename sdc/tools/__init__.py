"""SDC agent tools package.

Each agent gets:
  - 2 RAG tools (search_runbook, search_historical_records) bound to its
    own Chroma collections via closure
  - 3 domain tools specific to its ITIL function

Tool lists are module-level singletons (built once per process) to avoid
recreating closures on every LLM call.
"""
