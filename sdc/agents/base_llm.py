"""Shared LLM factory — attaches the OTel callback to every agent's ChatOllama."""

import os
from langchain_ollama import ChatOllama


def make_llm(agent_key: str) -> ChatOllama:
    """Return a ChatOllama instance with the OTel callback pre-attached."""
    try:
        from sdc_otel import SDCOTelCallback
        callbacks = [SDCOTelCallback(agent_key=agent_key)]
    except Exception:
        callbacks = []

    return ChatOllama(
        model=os.getenv("LLM_MODEL", "llama3.2"),
        temperature=0.1,
        callbacks=callbacks,
    )
