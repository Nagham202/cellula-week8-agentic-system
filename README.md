# Cellula Week 8 – Agentic System: Chat with Your Documents

## Overview

This project is a document-based **Agentic Retrieval-Augmented Generation (RAG) system** developed as part of the Cellula Technologies NLP Internship.

**Week 8** turns the Week 7 agentic RAG system into a complete, deployable system: a FastAPI REST API, voice questions, image upload with OCR, a PDF Report Generator Agent, an answer cache, a Docker image, and a Terraform configuration for deployment.

The application allows users to upload PDF, DOCX, and TXT documents, ask questions about their contents, and receive answers grounded in the uploaded documents with accurate source citations.

The system uses three specialized AI agents working together:

1. **Retriever Agent:** Searches the document knowledge base and retrieves relevant evidence.
2. **Analyst Agent:** Analyzes retrieved information, performs calculations, compares documents, extracts tables, and requests additional evidence when needed.
3. **Answer Agent:** Generates clear, structured, evidence-based answers with document citations.

An Orchestrator coordinates the agents, LangGraph manages the workflow, and the system is used through a FastAPI REST API or the Streamlit app.

---

## Features

### Week 8

- FastAPI REST API with interactive documentation at `/docs`.
- Voice questions: speech is converted to text, then answered (`/ask-voice`).
- Image upload with OCR: text found in images goes into the knowledge base (`/upload`).
- Report Generator Agent: professional PDF reports whose design the agent controls (`/report`).
- Answer cache: repeated questions are answered instantly with no LLM calls.
- Clear error responses (400, 404, 422, 503) and request logging.
- Docker image with a health check; API keys passed at run time.
- Terraform configuration (Docker provider) checked with `init`, `validate` and `plan`.
- Streamlit interface restyled in dark mode.

### Week 7

- Upload PDF, DOCX, and TXT documents.
- Automatic document loading, cleaning, and chunking.
- Dense and sparse embeddings stored in Qdrant.
- Hybrid semantic and keyword search.
- Query rewriting and alternative query generation.
- Metadata filtering by document, page, and chapter.
- Reranking and context selection.
- Multi-agent RAG architecture.
- Mathematical calculations using the Calculator tool.
- Table extraction and structured data analysis.
- Document comparison and metric analysis.
- Additional evidence retrieval through an Analyst feedback loop.
- Duplicate evidence detection and removal.
- Evidence-based answer generation.
- Source and page citations.
- Conversation history and follow-up questions.
- Interactive Streamlit interface.

---

## System Architecture

The project follows a three-agent workflow coordinated by an Orchestrator.

### 1. Document Processing Pipeline

Before the agents start working, uploaded documents pass through an automatic processing pipeline.

```text
PDF / DOCX / TXT
       |
       v
 Document Loading
       |
       v
 Text Cleaning
       |
       v
 Document Chunking
       |
       v
 Embedding Generation
       |
       v
 Qdrant Vector Database
```

### 2. Three-Agent Workflow

```text
          User Question
                |
                v
          Orchestrator
                |
                v
          Retriever Agent
                |
                v
         Initial Evidence
                |
                v
           Analyst Agent
                |
         +------+------+
         |             |
      Enough       Not Enough
      Evidence      Evidence
         |             |
         |             v
         |      Retrieve More
         |        Evidence
         |             |
         |<------------+
         |
         v
     Analysis Result
         |
         v
      Answer Agent
         |
         v
   Final Answer with
       Citations
```

The Orchestrator coordinates the process and ensures that the Answer Agent receives the Analyst's findings and the collected evidence.

### 3. Week 8: API and Deployment

```text
   Clients: Streamlit app · /docs page · any program
                        |
                        v
               FastAPI (api/main.py)
   /upload  /sources  /ask  /ask-voice  /report  /health
      |                 |        |          |
      |                 |   Speech to text  |
      v                 v        |          v
 Pipeline + OCR    Answer cache <+    Report Generator
      |                 |                 Agent (PDF)
      v                 v
   Qdrant  <---  Orchestrator -> Retriever -> Analyst -> Answer

   Packaging: Dockerfile -> image    Deployment: Terraform (infra/)
```

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| LangChain | Agent and tool development |
| LangGraph | Multi-agent workflow orchestration |
| Groq | Primary LLM provider |
| OpenRouter | Optional LLM fallback |
| Ollama | Optional local LLM fallback |
| Qdrant | Vector database |
| FastEmbed | Embedding generation and reranking |
| Streamlit | Web application interface |
| FastAPI + Uvicorn | REST API and server |
| Pydantic | Request and response validation |
| SQLite | Answer cache |
| Docker | Container image |
| Terraform | Infrastructure as Code |
| PyPDF | PDF text extraction |
| Python-docx | DOCX document processing |
| Pytest | Testing |

---

## Project Structure

```text
cellula-week8-agentic-system/
│
├── api/
│   ├── main.py
│   ├── schemas.py
│   ├── fakes.py
│   └── README.md
│
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── terraform.tfvars.example
│   ├── modules/app/
│   ├── results/
│   └── README.md
│
├── data/
│   ├── samples/
│   └── qdrant/
│
├── eval/
│   ├── questions.json
│   ├── compare_search.py
│   ├── compare_rerankers.py
│   └── results/
│
├── scripts/
│   └── check_end_to_end.py
│
├── src/
│   │
│   ├── analyst/
│   │   ├── analyst_agent.py
│   │   └── tools/
│   │       ├── calculator.py
│   │       ├── data_analysis.py
│   │       ├── document_comparison.py
│   │       ├── retrieve_more.py
│   │       └── table_extractor.py
│   │
│   ├── answer/
│   │   ├── answer_agent.py
│   │   └── formatters.py
│   │
│   ├── pipeline/
│   │   ├── chunking.py
│   │   ├── cleaning.py
│   │   ├── embeddings.py
│   │   ├── ingest.py
│   │   ├── loaders.py
│   │   └── store.py
│   │
│   ├── retriever/
│   │   ├── fake_retriever.py
│   │   ├── filters.py
│   │   ├── query_rewriter.py
│   │   ├── reranker.py
│   │   ├── retriever.py
│   │   ├── search.py
│   │   └── selector.py
│   │
│   ├── cache.py
│   ├── chat_graph.py
│   ├── llm.py
│   └── orchestrator.py
│
├── tests/
│
├── app.py
├── config.py
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Nagham202/cellula-week8-agentic-system.git
```

Navigate to the project directory:

```bash
cd cellula-week8-agentic-system
```

### 2. Create a Virtual Environment

Python 3.12 is recommended.

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file using the provided `.env.example`.

**Windows:**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Open `.env` and add your API keys:

```env
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

Groq is the primary provider. OpenRouter is optional and can be used as a fallback. Ollama can also be used as a local fallback when installed and running.

**Important:** Never upload your `.env` file or API keys to GitHub.

### 5. Check the LLM Configuration

Run:

```bash
python -m src.llm
```

This checks the configured LLM providers.

---

## Document Ingestion

The document ingestion pipeline processes uploaded files and stores their chunks in Qdrant.

Run:

```bash
python -m src.pipeline.ingest
```

The pipeline performs:

1. Document loading.
2. Text cleaning.
3. Document chunking.
4. Embedding generation.
5. Vector database storage.

The configured chunk size is 500 characters, with an overlap of 100 characters.

The local Qdrant database is generated on each developer's machine and is not committed to GitHub.

---

## The Three Agents

### 1. Retriever Agent

**Location:** `src/retriever/`

The Retriever Agent is responsible for finding relevant information from uploaded documents. It does not generate answers.

Its main components include:

- **Query Rewriter:** Rewrites questions to improve retrieval quality.
- **Semantic Search:** Finds information based on meaning.
- **Keyword Search:** Finds information based on exact words and phrases.
- **Metadata Filter:** Filters results by document, page, and chapter.
- **Hybrid Search:** Combines semantic and keyword retrieval.
- **Reranker:** Reorders retrieved candidates according to relevance.
- **Context Selector:** Selects useful evidence while reducing duplication.

The main retrieval functions are:

```python
from src.retriever.retriever import (
    retrieve,
    retrieve_more,
    retrieve_with_details
)

evidence = retrieve(question)

details = retrieve_with_details(question)

additional_evidence = retrieve_more(
    query="Find more details about the results",
    already_seen_ids=[]
)
```

### 2. Analyst Agent

**Location:** `src/analyst/`

The Analyst Agent receives the retrieved evidence and performs deeper analysis using five specialized tools.

#### Calculator Tool

File: `src/analyst/tools/calculator.py`

Supports:

- Addition
- Subtraction
- Multiplication
- Division
- Average
- Percentage
- Ratio

#### Table Extractor Tool

File: `src/analyst/tools/table_extractor.py`

Identifies pipe-separated text tables and converts them into structured columns and rows.

#### Document Comparison Tool

File: `src/analyst/tools/document_comparison.py`

Compares information across two documents, identifies similarities and differences, and compares shared percentage-based metrics.

#### Data Analysis Tool

File: `src/analyst/tools/data_analysis.py`

Performs statistical analysis, including:

- Mean
- Median
- Minimum and maximum
- Range
- Standard deviation
- Trend detection
- Model ranking

#### Retrieve More Evidence Tool

File: `src/analyst/tools/retrieve_more.py`

Allows the Analyst to request additional relevant document chunks when the initial evidence is insufficient.

It excludes previously retrieved chunk IDs to avoid duplicate evidence.

### 3. Answer Agent

**Location:** `src/answer/`

The Answer Agent receives:

- The user's question.
- The Analyst's findings.
- The retrieved document evidence.

Its responsibilities include:

- Generating the final response.
- Using only the provided evidence and analysis.
- Adding appropriate document citations.
- Formatting answers into paragraphs, lists, or tables.
- Handling questions that cannot be answered from the uploaded documents.

The citation formatter converts numbered references into document names and page numbers.

---

## Orchestrator

**Location:** `src/orchestrator.py`

The Orchestrator coordinates the Retriever and Analyst Agents and prepares the results for the Answer Agent.

Its main function is:

```python
from src.orchestrator import run_analysis

result = run_analysis(
    question="How does the paper evaluate its proposed method?",
    chat_history=None,
    top_k=6
)
```

The function returns a dictionary containing:

| Field | Description |
|---|---|
| `question` | Original user question |
| `initial_evidence` | Evidence retrieved initially |
| `additional_evidence` | Evidence retrieved through the Analyst |
| `all_evidence` | Combined evidence without duplicate chunk IDs |
| `analysis` | Analyst's findings |
| `retrieval_details` | Search query, filters, and other retrieval information |

If no evidence is found, the Orchestrator returns empty evidence lists and a message indicating that no relevant evidence was found.

---

## Running the Application

Start the Streamlit application from the project root:

```bash
python -m streamlit run app.py
```

The application provides:

- Document upload for PDF, DOCX, and TXT files.
- Adding documents to the knowledge base.
- Viewing stored documents and chunk counts.
- Deleting uploaded documents.
- Asking questions about uploaded documents.
- Asking follow-up questions using conversation history.
- Receiving answers supported by document citations.
- Clearing the current conversation.

---

## Using the Chat API

The project also provides a Python interface through LangGraph.

```python
from src.chat_graph import ask

question = "What are the main findings of the document?"

history = []

reply = ask(question, history)

print(reply["answer"])
print(reply["sources"])
```

The response contains:

- `answer`: Final generated answer.
- `sources`: Document sources used in the answer.
- `analysis`: The Analyst Agent's analysis (used by the report agent).
- `from_cache`: `true` when the answer came from the answer cache (no LLM calls).

Conversation history can be passed to support follow-up questions.

---

## REST API, Docker and Terraform (Week 8)

The system is also available as a FastAPI REST API, with endpoints to upload documents, list and delete sources,
ask by text or voice, and download PDF reports. It is packaged with a Dockerfile, and its infrastructure is
described with Terraform.

```bash
uvicorn api.main:app --reload        # then open http://127.0.0.1:8000/docs
```

- API endpoints, Docker and tests: [api/README.md](api/README.md)
- Terraform design, variables, and how to init/validate/plan: [infra/README.md](infra/README.md)

---

## Testing

The project uses Pytest for testing individual components and the agent workflow.

Run all tests:

```bash
python -m pytest -v
```

Run specific Analyst and Orchestrator tests:

```bash
python -m pytest tests/test_calculator.py -v
python -m pytest tests/test_data_analysis.py -v
python -m pytest tests/test_document_comparison.py -v
python -m pytest tests/test_retrieve_more.py -v
python -m pytest tests/test_table_extractor.py -v
python -m pytest tests/test_orchestrator.py -v
```

Run Answer Agent and workflow tests:

```bash
python -m pytest tests/test_answer_agent.py -v
python -m pytest tests/test_formatters.py -v
python -m pytest tests/test_chat_graph.py -v
```

Some tests require a populated Qdrant database and valid API credentials. Follow the relevant test setup before running them.

### Evaluation Scripts

Compare retrieval approaches:

```bash
python -m eval.compare_search
```

Compare reranker models:

```bash
python -m eval.compare_rerankers
```

Run the end-to-end document processing check:

```bash
python -m scripts.check_end_to_end
```

Evaluation results and experiment notes are available in `eval/results/` and `report_notes.md`.

---

## Configuration

Project settings are managed through `config.py`.

Important settings include:

| Setting | Default | Purpose |
|---|---|---|
| `CHUNK_SIZE` | 500 | Document chunk size |
| `CHUNK_OVERLAP` | 100 | Overlap between chunks |
| `DENSE_MODEL` | `BAAI/bge-small-en-v1.5` | Dense embedding model |
| `SPARSE_MODEL` | `Qdrant/bm25` | Sparse retrieval model |
| `TOP_K` | 6 | Default retrieved evidence count |
| `RERANK_CANDIDATES` | 20 | Candidates before reranking |
| `USE_RERANKER` | True | Enable reranking |
| `USE_QUERY_REWRITER` | True | Enable query rewriting |
| `LLM_PROVIDER` | `groq` | Primary LLM provider |
| `USE_FALLBACKS` | True | Enable LLM fallbacks |
| `LLM_TEMPERATURE` | 0 | LLM temperature |
| `USE_CACHE` | True | Enable the answer cache |
| `CACHE_TTL_SECONDS` | 86400 | How long cached answers are kept |
| `MAX_UPLOAD_MB` | 20 | Largest file the API accepts |

If the embedding model is changed, the local Qdrant database should be rebuilt because vectors from different embedding models are not interchangeable.

---

## Important Notes

- The current embedding and BM25 configuration is primarily English-oriented.
- Scanned PDFs containing images without extractable text may require OCR.
- Table extraction currently focuses on pipe-separated text tables.
- Document comparison uses percentage-based metric extraction and basic word-overlap analysis.
- DOCX and TXT documents do not have page numbers in the current evidence format. Their citations use document names.
- Qdrant local mode locks its database directory. Avoid opening the same local database from multiple running processes at once.
- Model availability and free-tier provider limits can change.

---

## Team Contributions

This project was developed collaboratively by a team of three members.

### Week 8

| Team Member | Responsibilities |
|---|---|
| **Nagham** | FastAPI deployment (all endpoints), answer cache, Dockerfile, and Terraform |
| **Sara** | Voice queries (speech to text) and image upload with OCR |
| **Heba** | Report Generator Agent (PDF reports) |

### Week 7

| Team Member | Responsibilities |
|---|---|
| **Nagham** | Document processing pipeline and Retriever Agent |
| **Sara** | Analyst Agent, five specialized tools, and Orchestrator |
| **Heba** | Answer Agent, citation formatting, LangGraph workflow, and Streamlit application |

---

## Future Improvements

- Enhance table extraction for complex PDF layouts.
- Improve support for multilingual and Arabic documents.
- Expand document comparison capabilities.
- Improve retrieval and answer evaluation.
- Add additional analytical tools.
- Continue improving the multi-agent workflow.
- Send chat history with voice questions, so spoken follow-ups work.
- Let the Streamlit app call the REST API instead of opening Qdrant directly.
- Move to a Qdrant server so several API containers can run at once.

---

## Repository

**GitHub:** https://github.com/Nagham202/cellula-week8-agentic-system

**Previous version (Week 7):** https://github.com/Nagham202/cellula-week7-agentic-rag

**Developed as part of the Cellula Technologies NLP Internship – Week 8.**
