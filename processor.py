"""LLM Processor — companion service for llm-demo.

Pre-processes prompts (sanitise, enrich metadata) and post-processes
responses (word count, reading time, sentiment tag) before returning
them to the main service.

Runs on port 8001. Started automatically by app.py.
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

_tracer: Optional[trace.Tracer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tracer
    from otel import setup_telemetry
    setup_telemetry(app, service_name="llm-processor")
    _tracer = trace.get_tracer("llm-processor")
    logger.info("LLM Processor ready — http://localhost:8001")
    yield
    logger.info("LLM Processor shutting down")


app = FastAPI(title="LLM Processor · Dash0", lifespan=lifespan)


# ── Models ───────────────────────────────────────────────────────────────────

class PreRequest(BaseModel):
    prompt: str
    session_id: str = "unknown"


class PreResponse(BaseModel):
    prompt: str
    original_prompt: str
    word_count: int
    char_count: int
    session_id: str


class PostRequest(BaseModel):
    response: str
    session_id: str = "unknown"


class PostResponse(BaseModel):
    response: str
    word_count: int
    sentence_count: int
    reading_time_s: float
    sentiment: str
    session_id: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "llm-processor"}


@app.post("/pre", response_model=PreResponse)
def pre_process(req: PreRequest):
    """Sanitise and enrich the user prompt before it reaches the LLM."""
    with _tracer.start_as_current_span("processor.pre", kind=trace.SpanKind.SERVER) as span:
        span.set_attribute("peer.service", "llm-demo")
        span.set_attribute("session.id", req.session_id)

        # Sanitise: collapse whitespace, strip control characters
        clean = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", req.prompt).strip()
        clean = re.sub(r"\s+", " ", clean)

        word_count = len(clean.split())
        char_count = len(clean)

        span.set_attribute("prompt.word_count", word_count)
        span.set_attribute("prompt.char_count", char_count)

        logger.info(
            "pre-process session=%s words=%d chars=%d",
            req.session_id, word_count, char_count,
        )

        return PreResponse(
            prompt=clean,
            original_prompt=req.prompt,
            word_count=word_count,
            char_count=char_count,
            session_id=req.session_id,
        )


@app.post("/post", response_model=PostResponse)
def post_process(req: PostRequest):
    """Enrich the LLM response with metadata before returning it to the user."""
    with _tracer.start_as_current_span("processor.post", kind=trace.SpanKind.SERVER) as span:
        span.set_attribute("peer.service", "llm-demo")
        span.set_attribute("session.id", req.session_id)

        words = req.response.split()
        sentences = re.split(r"[.!?]+", req.response)
        word_count = len(words)
        sentence_count = max(1, len([s for s in sentences if s.strip()]))
        reading_time_s = round(word_count / 200 * 60, 1)  # 200 wpm

        # Naive sentiment: count positive vs negative keywords
        pos = sum(req.response.lower().count(w) for w in ["good", "great", "yes", "correct", "sure", "help"])
        neg = sum(req.response.lower().count(w) for w in ["no", "not", "error", "fail", "wrong", "sorry"])
        sentiment = "positive" if pos > neg else ("negative" if neg > pos else "neutral")

        span.set_attribute("response.word_count", word_count)
        span.set_attribute("response.sentence_count", sentence_count)
        span.set_attribute("response.reading_time_s", reading_time_s)
        span.set_attribute("response.sentiment", sentiment)

        logger.info(
            "post-process session=%s words=%d reading_time=%.1fs sentiment=%s",
            req.session_id, word_count, reading_time_s, sentiment,
        )

        return PostResponse(
            response=req.response,
            word_count=word_count,
            sentence_count=sentence_count,
            reading_time_s=reading_time_s,
            sentiment=sentiment,
            session_id=req.session_id,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
