# Cellula Week 8 – Agentic RAG System

An intelligent document question-answering system that uses multiple specialized AI agents to retrieve information, analyze evidence, and generate accurate answers with document citations.

The project extends the previous RAG system with additional capabilities, including image OCR, voice-based queries, report generation, and API deployment infrastructure.

## Project Overview

The system allows users to upload documents, ask questions using text or voice, and receive answers based on the uploaded content.

Instead of relying on a single AI model to perform every task, the system uses specialized agents that collaborate through an orchestrated workflow.

## Main Features

### 1. Document Processing and RAG Pipeline
- Upload PDF, DOCX, and TXT documents.
- Clean and preprocess extracted text.
- Split documents into smaller chunks.
- Generate embeddings for document chunks.
- Store and retrieve information using Qdrant.
- Support hybrid retrieval using semantic and keyword search.
- Improve retrieval results through query rewriting and reranking.

### 2. Multi-Agent Workflow

The system uses three specialized agents:

**Retriever Agent**
- Searches the vector database for relevant document information.
- Uses query rewriting to improve search queries.
- Performs semantic and keyword-based retrieval.
- Applies reranking and context selection to identify the most relevant evidence.

**Analyst Agent**
- Analyzes and combines retrieved evidence.
- Performs calculations using the Calculator tool.
- Extracts structured information using the Table Extractor.
- Compares information across multiple documents.
- Performs data analysis.
- Requests additional evidence when the initial results are insufficient.

**Answer Agent**
- Generates clear and organized answers.
- Uses the evidence and analysis provided by the previous agents.
- Includes document references and citations in the final response.

**Orchestrator**

Coordinates the agents and manages the workflow between retrieval, analysis, and answer generation.

### 3. Image Upload and OCR
- Upload images containing text.
- Extract text from images using Tesseract OCR.
- Support English and Arabic text recognition.
- Preprocess images to improve OCR results.
- Send extracted text into the existing RAG ingestion pipeline.
- Ask questions about information extracted from uploaded images.

### 4. Voice Query Integration
- Record questions directly through the application.
- Convert recorded audio into text using speech-to-text.
- Display the recognized question.
- Send the transcribed question to the existing RAG workflow.
- Receive answers with the same retrieval and citation functionality as text-based questions.

### 5. Report Generator Agent
- Generate reports using information processed by the system.
- Organize relevant information into structured report content.
- Support the report-generation workflow through a dedicated agent.

### 6. FastAPI Backend
- Provides API endpoints for interacting with the system.
- Supports backend integration with the application's functionality.
- Separates API functionality from the user interface.

### 7. Terraform Infrastructure
- Uses Terraform for infrastructure as code.
- Supports infrastructure configuration and deployment workflows.

### 8. Streamlit User Interface
- Chat interface for asking questions.
- Document and image upload.
- Voice recording and transcription.
- Conversation history.
- Knowledge-base source management.
- Display of generated answers and their sources.

## System Architecture

The main question-answering workflow:

1. The user uploads documents or images.
2. The ingestion pipeline extracts and processes the content.
3. The content is divided into chunks and stored in Qdrant.
4. The user submits a question using text or voice.
5. The Orchestrator coordinates the Retriever Agent, Analyst Agent, and Answer Agent.
6. The Retriever Agent finds relevant evidence.
7. The Analyst Agent analyzes the evidence and can request additional information.
8. The Answer Agent generates the final response with citations.
9. The application displays the answer to the user.

## Technologies Used

- **Python** – Main programming language.
- **Streamlit** – User interface.
- **LangChain** – LLM and tool integration.
- **LangGraph** – Agent workflow orchestration.
- **Groq** – LLM and speech-to-text services.
- **OpenRouter** – Alternative LLM provider.
- **Qdrant** – Vector database.
- **Hugging Face** – Embedding and reranking models.
- **Tesseract OCR** – Image text extraction.
- **Pillow** – Image preprocessing.
- **FastAPI** – Backend API.
- **Terraform** – Infrastructure as code.

## Project Structure

```text
cellula-week8-agentic-system/
│
├── app.py
├── config.py
├── requirements.txt
│
├── api/
│   └── main.py
│
├── src/
│   ├── analyst/
│   │   └── tools/
│   ├── pipeline/
│   │   ├── ocr.py
│   │   ├── ingest.py
│   │   ├── chunking.py
│   │   ├── cleaning.py
│   │   ├── loaders.py
│   │   └── store.py
│   │
│   ├── report/
│   │   └── report_agent.py
│   │
│   ├── voice.py
│   ├── chat_graph.py
│   ├── orchestrator.py
│   └── llm.py
│
├── tests/
│
├── data/
│   └── qdrant/
│
└── README.md
```

*Note: The structure above highlights the main project components. Additional files and infrastructure configuration may exist in the repository.*

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Nagham202/cellula-week8-agentic-system.git

cd cellula-week8-agentic-system
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

Add any other environment variables required by the project configuration.

### 5. Install Tesseract OCR

Image OCR requires Tesseract to be installed on the machine.

Download it from:

https://github.com/UB-Mannheim/tesseract/wiki

Make sure the Tesseract executable is accessible to the application and that the required language data is installed.

### 6. Run the Streamlit Application

```bash
streamlit run app.py
```

## Usage

1. Start the application.
2. Upload PDF, DOCX, TXT, or supported image files.
3. Add the files to the knowledge base.
4. Ask questions through the chat input or record a voice question.
5. Review the generated answers and document citations.
6. Use the report-generation functionality when a report is needed.

## Team Contributions

The project was developed collaboratively, with responsibilities divided across different components:

| Component | Responsibility |
|---|---|
| Image OCR | Image text extraction and integration into the RAG pipeline |
| Voice Query Integration | Audio recording, speech-to-text, and voice question processing |
| Report Generator Agent | Automated report generation |
| FastAPI Backend | API development and backend integration |
| Terraform | Infrastructure as code and deployment configuration |
| Agentic RAG System | Document retrieval, analysis, orchestration, and answer generation |

## Important Notes

- The system generates answers using information retrieved from the uploaded knowledge base.
- Answer citations help users identify the sources used.
- OCR accuracy depends on image quality, text clarity, and language.
- Voice transcription accuracy depends on audio quality and speech clarity.
- API keys should be stored in `.env` and should never be committed to GitHub.
- Local Qdrant storage should not be accessed simultaneously by multiple processes.

## Repository

GitHub: https://github.com/Nagham202/cellula-week8-agentic-system

---

**Cellula Week 8 – Agentic System**

A collaborative AI system combining document retrieval, multi-agent reasoning, image OCR, voice interaction, report generation, and backend infrastructure.
