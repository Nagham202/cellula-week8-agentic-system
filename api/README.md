# REST API (FastAPI)

The FastAPI app exposes the Week 7 "chat with your documents" system over HTTP, so any client (the web UI,
a voice recorder, a script) can upload documents, ask questions and get PDF reports.

```
Clients (Streamlit, /docs page, any program)
        │  HTTP (JSON / files)
        ▼
api/main.py ── /upload ─────────► src/pipeline (ingest_file, ingest_text) ─┐
            ── /sources ────────► src/pipeline/store                        ├─► Qdrant (data/qdrant)
            ── /ask, /ask-voice ► src/chat_graph.ask()                      │   answer cache (data/cache.sqlite3)
                                   (cache → Orchestrator → Retriever ───────┘
                                    → Analyst → Answer Agent)
            ── /ask-voice ──────► transcribe()        (teammate 2)
            ── /upload (images) ► extract_text()      (teammate 2)
            ── /report ─────────► generate_report()   (teammate 3)
```

## Run it

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint in the browser.

Local Qdrant (`data/qdrant`) can only be opened by **one program at a time**. Stop the Streamlit app before
starting the API, and run uvicorn with a single worker. If the database is locked, the server stops at startup
with a clear message.

## Endpoints

| Method | Path | Input | Output | Errors |
|---|---|---|---|---|
| GET | `/health` | none | `{"status": "ok"}` | none |
| POST | `/upload` | file: PDF, DOCX, TXT, PNG, JPG, JPEG (max 20 MB) | `{"filename", "chunks"}` | 400 wrong type, too big, no text |
| GET | `/sources` | none | `{"sources": [{"name", "chunks"}], "total_chunks"}` | none |
| DELETE | `/sources/{name}` | file name in the URL | `{"message"}` | 404 unknown name |
| POST | `/ask` | JSON `{"question", "chat_history": [{"role", "content"}]}` | `{"answer", "sources", "analysis", "from_cache"}` | 422 bad input, 503 LLM down |
| POST | `/ask-voice` | audio file: WAV, MP3, M4A, WEBM, OGG | same as `/ask` plus `"transcript"` | 400 wrong type or no speech, 503 LLM down |
| POST | `/report` | JSON `{"question", "answer", "analysis", "sources", "style"}` | PDF file (`report.pdf`) | 422 empty question or answer |

Any unexpected error returns `500` with a short JSON message. The details go to `logs/api.log`.

### Example: a question, then a follow-up

```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "What does error E31 mean?", "chat_history": []}'

curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "How do I fix it?",
          "chat_history": [{"role": "user", "content": "What does error E31 mean?"},
                           {"role": "assistant", "content": "E31 means the lidar sensor is blocked."}]}'
```

The API is **stateless**: the client sends the earlier messages with every `/ask`.

### Example: a PDF report

Send the fields from an `/ask` reply to `/report`. `style` is optional, given in plain words, and the report
agent turns it into fonts, sizes and colors.

```bash
curl -X POST http://127.0.0.1:8000/report -H "Content-Type: application/json" -o report.pdf \
     -d '{"question": "What does error E31 mean?", "answer": "...", "analysis": "...",
          "sources": ["kito_manual.pdf, page 3"], "style": "formal, navy headings"}'
```

## Answer cache

The same question returns the saved answer with 0 LLM calls (about 0.002 s instead of about 2.5 s). The cache key
is the normalized question plus the model settings. The cache is cleared whenever documents are added or
deleted. Follow-up questions in a conversation, and answers without sources, are not cached.
`python -m src.cache` shows how many answers are saved, and `python -m src.cache clear` deletes them.

## Teammates' functions (contracts)

`api/fakes.py` has stand-in versions with the agreed names, so the API works and can be tested now:

```python
transcribe(audio_path: str) -> str            # teammate 2: speech to text ("" if no speech)
extract_text(image_path: str) -> str          # teammate 2: OCR
generate_report(question: str, answer: str, analysis: str,
                sources: list[str], style: str | None) -> str   # teammate 3: returns the PDF path
```

To connect the real code, change this one import in `api/main.py`:

```python
from api.fakes import extract_text, generate_report, transcribe
```

## Files

| File | What it does |
|---|---|
| `api/main.py` | the endpoints, upload checks, error handling, logging, model loading at startup |
| `api/schemas.py` | Pydantic models for every request and response (shown on `/docs`) |
| `api/fakes.py` | stand-ins for the teammates' functions |
| `tests/test_api.py` | 24 tests for every endpoint (fakes and a temporary database, no LLM calls) |
| `Dockerfile`, `.dockerignore` | the container image (see below) |

## Tests

```bash
python -m pytest tests/test_api.py -v
```

## Docker

```bash
docker build -t docs-chat-api .
docker run --rm -p 8000:8000 --env-file .env -v "$(pwd)/data:/app/data" docs-chat-api
```

- The API keys are **not** in the image. They are passed with `--env-file` when the container starts.
- The embedding and reranker models are downloaded during the build, so the container starts offline.
- `/app/data` (Qdrant, cache, reports) is a volume, so the data survives restarts.
- The image has a health check that calls `/health` every 30 s.

To deploy the container with Terraform, see [infra/README.md](../infra/README.md).
