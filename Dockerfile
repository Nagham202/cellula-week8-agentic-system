FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/models

# before the code, so this layer stays cached when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY src/ src/
COPY api/ api/

# download the models at build time
RUN python -c "from src.pipeline.embeddings import get_dense_model, get_sparse_model; \
from src.retriever.reranker import get_reranker; import config; \
get_dense_model(); get_sparse_model(); get_reranker(config.RERANKER_MODEL)"

VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# one worker, local qdrant only allows one process
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
