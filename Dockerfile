FROM python:3.12-slim

WORKDIR /app

# chromadb pulls in onnxruntime which needs a C++ compiler on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so the ingest Job doesn't need internet access
# at runtime (all-MiniLM-L6-v2 via chromadb's DefaultEmbeddingFunction, ~90 MB)
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()"

COPY sdc/ ./sdc/
COPY static/ ./static/
COPY sdc_app.py sdc_otel.py ./

EXPOSE 8000

CMD ["uvicorn", "sdc_app:app", "--host", "0.0.0.0", "--port", "8000"]
