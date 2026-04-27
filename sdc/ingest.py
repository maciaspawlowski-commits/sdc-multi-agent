"""One-time ingestion script — loads runbooks and historical records into Chroma.

Two collection types per agent:
  sdc_runbook_{key}  — procedural runbook markdown chunks
  sdc_records_{key}  — synthetic historical operational records

Run once (or after updating content):
    python -m sdc.ingest

Re-running is safe: collections are cleared and rebuilt from scratch each time.
"""

import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RUNBOOK_DIR = Path(__file__).parent / "runbooks"
RECORDS_DIR = Path(__file__).parent / "records"

CHUNK_SIZE = 400      # target words per chunk
CHUNK_OVERLAP = 60    # words overlap between consecutive chunks

AGENT_RUNBOOKS = {
    "incident": "incident.md",
    "change":   "change.md",
    "problem":  "problem.md",
    "service":  "service.md",
    "sla":      "sla.md",
}

AGENT_RECORDS = {
    "incident": "incident_records.md",
    "change":   "change_records.md",
    "problem":  "problem_records.md",
    "service":  "service_records.md",
    "sla":      "sla_records.md",
}


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _split_by_heading(text: str) -> list[str]:
    """Primary split: by markdown headings (##, ###)."""
    sections = re.split(r"\n(?=#{1,3} )", text)
    return [s.strip() for s in sections if s.strip()]


def _split_by_record_separator(text: str) -> list[str]:
    """Split records file by '---' record separators, keeping each record intact."""
    sections = re.split(r"\n---\n", text)
    return [s.strip() for s in sections if s.strip() and len(s.split()) >= 20]


def _split_by_words(text: str, size: int, overlap: int) -> list[str]:
    """Sliding window over words for sections that are too long."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap
    return chunks


def chunk_runbook(text: str) -> list[str]:
    """Split a runbook into semantic chunks suitable for embedding."""
    sections = _split_by_heading(text)
    chunks: list[str] = []
    for section in sections:
        word_count = len(section.split())
        if word_count <= CHUNK_SIZE:
            chunks.append(section)
        else:
            chunks.extend(_split_by_words(section, CHUNK_SIZE, CHUNK_OVERLAP))
    return [c for c in chunks if len(c.split()) >= 10]


def chunk_records(text: str) -> list[str]:
    """Split a records file: each '---' separated record becomes one chunk.

    Records that are too long are sub-chunked by sliding window.
    Records are kept as whole units when possible — they represent single
    incidents/changes/problems and should be retrieved together.
    """
    # First try splitting by record separator
    sections = _split_by_record_separator(text)

    # Skip the title section (first element if it's just the file header)
    if sections and not sections[0].startswith("##"):
        sections = sections[1:]

    chunks: list[str] = []
    for section in sections:
        word_count = len(section.split())
        if word_count <= CHUNK_SIZE:
            chunks.append(section)
        else:
            # Very long record — sub-chunk but keep first 60 words as context prefix
            prefix_words = section.split()[:60]
            prefix = " ".join(prefix_words)
            sub = _split_by_words(section, CHUNK_SIZE, CHUNK_OVERLAP)
            # Prepend the record header to sub-chunks that don't start at the top
            chunks.append(sub[0])  # first sub-chunk already has the header
            for s in sub[1:]:
                chunks.append(prefix + " [...]\n\n" + s)

    return [c for c in chunks if len(c.split()) >= 20]


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def _ingest_collection(
    client,
    col_getter,
    col_name_fn,
    agent_key: str,
    file_path: Path,
    chunk_fn,
    collection_type: str,
) -> int:
    """Generic ingest: chunk a file and load into a Chroma collection."""
    if not file_path.exists():
        logger.warning("%s file not found: %s — skipping", collection_type, file_path)
        return 0

    text = file_path.read_text(encoding="utf-8")
    chunks = chunk_fn(text)
    logger.info(
        "Agent '%s' [%s]: %d chunks from %s",
        agent_key, collection_type, len(chunks), file_path.name,
    )

    # Drop and recreate for clean re-ingestion
    col_name = col_name_fn(agent_key)
    try:
        client.delete_collection(col_name)
        logger.debug("Dropped existing collection '%s'", col_name)
    except Exception:
        pass  # didn't exist yet

    col = col_getter(agent_key)

    ids = [f"{agent_key}_{collection_type}_{i:04d}" for i in range(len(chunks))]
    metadatas = [
        {"agent": agent_key, "type": collection_type, "chunk_index": i}
        for i in range(len(chunks))
    ]

    col.add(documents=chunks, ids=ids, metadatas=metadatas)
    count = col.count()
    logger.info(
        "Agent '%s' [%s]: %d documents stored in Chroma ✓",
        agent_key, collection_type, count,
    )
    return count


def ingest_all(force: bool = True) -> dict[str, dict[str, int]]:
    from sdc.vectorstore import (
        get_collection,
        get_records_collection,
        runbook_collection_name,
        records_collection_name,
        _get_client,
    )

    client = _get_client()
    summary: dict[str, dict[str, int]] = {}

    for agent_key in AGENT_RUNBOOKS:
        agent_summary: dict[str, int] = {}

        # --- Runbooks ---
        runbook_file = RUNBOOK_DIR / AGENT_RUNBOOKS[agent_key]
        agent_summary["runbooks"] = _ingest_collection(
            client=client,
            col_getter=get_collection,
            col_name_fn=runbook_collection_name,
            agent_key=agent_key,
            file_path=runbook_file,
            chunk_fn=chunk_runbook,
            collection_type="runbooks",
        )

        # --- Historical Records ---
        records_file = RECORDS_DIR / AGENT_RECORDS[agent_key]
        agent_summary["records"] = _ingest_collection(
            client=client,
            col_getter=get_records_collection,
            col_name_fn=records_collection_name,
            agent_key=agent_key,
            file_path=records_file,
            chunk_fn=chunk_records,
            collection_type="records",
        )

        summary[agent_key] = agent_summary

    return summary


if __name__ == "__main__":
    logger.info("Starting SDC ingestion (runbooks + historical records)...")
    results = ingest_all()

    logger.info("=" * 60)
    total_runbooks = 0
    total_records = 0
    for agent_key, counts in results.items():
        rb = counts.get("runbooks", 0)
        rec = counts.get("records", 0)
        total_runbooks += rb
        total_records += rec
        logger.info(
            "  %-10s  runbooks: %3d  records: %3d  total: %3d",
            agent_key, rb, rec, rb + rec,
        )

    logger.info("=" * 60)
    logger.info(
        "Total: %d runbook chunks + %d record chunks = %d documents across %d agent pairs",
        total_runbooks, total_records, total_runbooks + total_records, len(results),
    )
