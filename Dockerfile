# The FastAPI app in a container.
# build: docker build -t docs-chat-api .
# run:   docker run -p 8000:8000 --env-file .env -v "$(pwd)/data:/app/data" docs-chat-api

FROM python:3.12-slim

WORKDIR /app

# no .pyc files, and print logs right away instead of keeping them in a buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/models

# requirements first: Docker reuses this slow step when only our code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY src/ src/
COPY api/ api/

# download the embedding and reranker models into the image, so the container starts without the internet
RUN python -c "from src.pipeline.embeddings import get_dense_model, get_sparse_model; \
from src.retriever.reranker import get_reranker; import config; \
get_dense_model(); get_sparse_model(); get_reranker(config.RERANKER_MODEL)"

# Qdrant, the answer cache and reports live here; mount a folder or volume so they survive restarts
VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# one worker: local Qdrant can only be opened by one process
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
