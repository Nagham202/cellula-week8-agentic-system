import logging
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

import config
# fakes until the real voice/OCR/report code is ready
from api.fakes import extract_text, generate_report, transcribe
from api.schemas import (AskRequest, AskResponse, AskVoiceResponse, Message, ReportRequest, SourceInfo,
                         SourceList, UploadResult)
from src.answer.answer_agent import ERROR_MESSAGE
from src.chat_graph import ask
from src.pipeline.embeddings import get_dense_model, get_sparse_model
from src.pipeline.ingest import ingest_file, ingest_text
from src.pipeline.loaders import SourceError
from src.pipeline.store import count_chunks, delete_source, get_client, list_sources
from src.retriever.reranker import get_reranker

DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler("logs/api.log")])
logger = logging.getLogger("api")

LLM_DOWN_MESSAGE = "The AI service is not available right now. Please try again in a minute."


@asynccontextmanager
async def lifespan(app):
    logger.info("Loading the models and opening Qdrant...")
    get_dense_model()
    get_sparse_model()
    if config.USE_RERANKER:
        get_reranker(config.RERANKER_MODEL)
    # open qdrant now so a locked db fails at startup, not on the first request
    get_client()
    logger.info("Ready")
    yield


app = FastAPI(
    title="Chat with your documents API",
    description="Upload documents, ask questions about them, and get answers with sources.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
def unexpected_error(request: Request, error: Exception):
    logger.error(f"Unexpected error on {request.method} {request.url.path}", exc_info=error)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. "
                                                            "The details are in logs/api.log."})


def answer_or_503(question, history=None):
    start = time.perf_counter()
    try:
        reply = ask(question, history)
    except Exception:
        logger.exception(f"ask() failed for {question[:80]!r}")
        raise HTTPException(status_code=503, detail=LLM_DOWN_MESSAGE)
    # the answer agent returns this message instead of raising when the LLM fails
    if reply["answer"] == ERROR_MESSAGE:
        logger.error(f"The Answer Agent could not reach an LLM for {question[:80]!r}")
        raise HTTPException(status_code=503, detail=LLM_DOWN_MESSAGE)
    logger.info(f"Answered {question[:80]!r} in {time.perf_counter() - start:.1f} s "
                f"(from_cache={reply['from_cache']}, sources={len(reply['sources'])})")
    return reply


def read_upload(file, allowed_extensions):
    # drop any folders from the name, e.g. ../../x.pdf
    filename = Path(file.filename).name
    extension = Path(filename).suffix.lower()
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        logger.warning(f"Rejected {filename}: unsupported type {extension}")
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}. Allowed: {allowed}.")

    content = file.file.read()
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        logger.warning(f"Rejected {filename}: larger than {config.MAX_UPLOAD_MB} MB")
        raise HTTPException(status_code=400, detail=f"{filename} is larger than {config.MAX_UPLOAD_MB} MB.")
    return filename, content


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResult)
def upload(file: UploadFile):
    filename, content = read_upload(file, DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS)

    # keep the real file name, it's used as the source in citations
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / filename
        path.write_bytes(content)
        try:
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                chunk_count = ingest_text(extract_text(str(path)), filename)
            else:
                chunk_count = ingest_file(path)
        except SourceError as error:
            logger.warning(f"Upload rejected: {error}")
            raise HTTPException(status_code=400, detail=str(error))
    logger.info(f"Uploaded {filename}: {chunk_count} chunks")
    return UploadResult(filename=filename, chunks=chunk_count)


@app.get("/sources", response_model=SourceList)
def get_sources():
    sources = [SourceInfo(name=name, chunks=count_chunks(name)) for name in list_sources()]
    return SourceList(sources=sources, total_chunks=sum(source.chunks for source in sources))


@app.delete("/sources/{name}", response_model=Message)
def remove_source(name: str):
    if name not in list_sources():
        raise HTTPException(status_code=404, detail=f"No source called {name}.")
    delete_source(name)
    logger.info(f"Deleted {name}")
    return Message(message=f"{name} was deleted.")


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    history = [message.model_dump() for message in request.chat_history]
    reply = answer_or_503(request.question, history)
    return AskResponse(**reply)


@app.post("/ask-voice", response_model=AskVoiceResponse)
def ask_voice(file: UploadFile):
    filename, content = read_upload(file, AUDIO_EXTENSIONS)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / filename
        path.write_bytes(content)
        transcript = transcribe(str(path))

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="No speech could be heard in the audio.")
    logger.info(f"Heard: {transcript[:80]!r}")
    reply = answer_or_503(transcript)
    return AskVoiceResponse(transcript=transcript, **reply)


@app.post("/report")
def make_report(request: ReportRequest):
    pdf_path = generate_report(request.question, request.answer, request.analysis, request.sources, request.style)
    logger.info(f"Report made: {pdf_path}")
    return FileResponse(pdf_path, media_type="application/pdf", filename="report.pdf")
