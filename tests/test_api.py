# tests for every endpoint: no LLM calls (ask() is replaced by a fake) and a temporary Qdrant folder

import pytest
from fastapi.testclient import TestClient

import config
from api import fakes, main
from src.answer.answer_agent import ERROR_MESSAGE
from src.pipeline import store

FAKE_REPLY = {"answer": "E31 means the lidar sensor is blocked [kito_manual.pdf, page 3].",
              "sources": ["kito_manual.pdf, page 3"],
              "analysis": "The manual says E31 = lidar blocked.",
              "from_cache": False}


@pytest.fixture
def client(tmp_path, monkeypatch):
    # a temporary database, so the real data/qdrant is never touched
    monkeypatch.setattr(config, "QDRANT_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setattr(store, "client", None)
    monkeypatch.setattr(fakes, "REPORTS_DIR", tmp_path / "reports")
    # the real ask() calls three LLMs; this fake answers instantly and remembers what it got
    calls = []

    def fake_ask(question, chat_history=None):
        calls.append({"question": question, "chat_history": chat_history})
        return FAKE_REPLY

    monkeypatch.setattr(main, "ask", fake_ask)
    test_client = TestClient(main.app, raise_server_exceptions=False)
    test_client.ask_calls = calls
    return test_client


def upload(client, filename, content):
    return client.post("/upload", files={"file": (filename, content)})


# ---------- /health ----------

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------- /upload ----------

def test_upload_text_file_adds_chunks(client):
    response = upload(client, "notes.txt", b"The office opens at 8 am. Parking is behind the building.")
    assert response.status_code == 200
    assert response.json()["filename"] == "notes.txt"
    assert response.json()["chunks"] >= 1


def test_upload_image_goes_through_ocr(client):
    response = upload(client, "office_sign.png", b"fake image bytes")
    assert response.status_code == 200
    # the image name is the source, so citations show where the text came from
    assert client.get("/sources").json()["sources"][0]["name"] == "office_sign.png"


def test_upload_rejects_unsupported_type(client):
    response = upload(client, "script.py", b"print('hi')")
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_file_that_is_too_big(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0)
    response = upload(client, "notes.txt", b"some text")
    assert response.status_code == 400
    assert "larger than" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = upload(client, "empty.txt", b"")
    assert response.status_code == 400


def test_upload_keeps_only_the_file_name(client):
    # a name like ../../x.txt must not be saved outside the temporary folder
    response = upload(client, "../../outside.txt", b"Some text for the test.")
    assert response.status_code == 200
    assert response.json()["filename"] == "outside.txt"


# ---------- /sources ----------

def test_sources_empty_at_start(client):
    assert client.get("/sources").json() == {"sources": [], "total_chunks": 0}


def test_sources_lists_uploaded_files_with_chunk_counts(client):
    upload(client, "a.txt", b"First file about robots.")
    upload(client, "b.txt", b"Second file about the office.")
    data = client.get("/sources").json()
    assert [source["name"] for source in data["sources"]] == ["a.txt", "b.txt"]
    assert data["total_chunks"] == sum(source["chunks"] for source in data["sources"])


def test_delete_source(client):
    upload(client, "a.txt", b"First file about robots.")
    response = client.delete("/sources/a.txt")
    assert response.status_code == 200
    assert client.get("/sources").json()["sources"] == []


def test_delete_unknown_source_gives_404(client):
    response = client.delete("/sources/nope.pdf")
    assert response.status_code == 404


# ---------- /ask ----------

def test_ask_returns_answer_sources_and_analysis(client):
    response = client.post("/ask", json={"question": "What does error E31 mean?"})
    assert response.status_code == 200
    assert response.json() == FAKE_REPLY


def test_ask_passes_the_chat_history_as_dicts(client):
    history = [{"role": "user", "content": "What does error E31 mean?"},
               {"role": "assistant", "content": "The lidar sensor is blocked."}]
    client.post("/ask", json={"question": "How do I fix it?", "chat_history": history})
    assert client.ask_calls == [{"question": "How do I fix it?", "chat_history": history}]


def test_ask_rejects_empty_question(client):
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422
    assert client.ask_calls == []


def test_ask_rejects_unknown_role(client):
    response = client.post("/ask", json={"question": "Hi", "chat_history": [{"role": "robot", "content": "x"}]})
    assert response.status_code == 422


def test_ask_gives_503_when_the_llm_is_down(client, monkeypatch):
    def broken_ask(question, chat_history=None):
        raise ConnectionError("every provider failed")

    monkeypatch.setattr(main, "ask", broken_ask)
    response = client.post("/ask", json={"question": "What does error E31 mean?"})
    assert response.status_code == 503
    assert "not available" in response.json()["detail"]


def test_ask_gives_503_when_the_answer_agent_returns_its_error_message(client, monkeypatch):
    monkeypatch.setattr(main, "ask", lambda question, chat_history=None:
                        {"answer": ERROR_MESSAGE, "sources": [], "analysis": "", "from_cache": False})
    response = client.post("/ask", json={"question": "What does error E31 mean?"})
    assert response.status_code == 503


# ---------- /ask-voice ----------

def test_ask_voice_returns_transcript_and_answer(client):
    response = client.post("/ask-voice", files={"file": ("question.m4a", b"fake audio")})
    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == "What does error E31 mean?"
    assert data["answer"] == FAKE_REPLY["answer"]
    # the transcript is what gets asked
    assert client.ask_calls[0]["question"] == "What does error E31 mean?"


def test_ask_voice_rejects_non_audio_file(client):
    response = client.post("/ask-voice", files={"file": ("question.txt", b"hello")})
    assert response.status_code == 400


def test_ask_voice_with_no_speech_gives_400(client, monkeypatch):
    monkeypatch.setattr(main, "transcribe", lambda audio_path: "  ")
    response = client.post("/ask-voice", files={"file": ("silence.wav", b"fake audio")})
    assert response.status_code == 400
    assert client.ask_calls == []


# ---------- /report ----------

def test_report_returns_a_pdf(client):
    body = {"question": "What does error E31 mean?", "answer": FAKE_REPLY["answer"],
            "analysis": FAKE_REPLY["analysis"], "sources": FAKE_REPLY["sources"], "style": "formal"}
    response = client.post("/report", json=body)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_report_passes_everything_to_the_report_agent(client, monkeypatch, tmp_path):
    received = {}

    def fake_generate_report(question, answer, analysis, sources, style=None):
        received.update(question=question, answer=answer, analysis=analysis, sources=sources, style=style)
        path = tmp_path / "r.pdf"
        path.write_bytes(b"%PDF-1.4 test")
        return str(path)

    monkeypatch.setattr(main, "generate_report", fake_generate_report)
    client.post("/report", json={"question": "q", "answer": "a", "analysis": "x", "sources": ["s"],
                                 "style": "navy headings"})
    assert received == {"question": "q", "answer": "a", "analysis": "x", "sources": ["s"],
                        "style": "navy headings"}


def test_report_rejects_empty_answer(client):
    response = client.post("/report", json={"question": "q", "answer": ""})
    assert response.status_code == 422


# ---------- unexpected errors ----------

def test_unexpected_error_gives_500_json(client, monkeypatch):
    def broken_list_sources():
        raise KeyError("a bug")

    monkeypatch.setattr(main, "list_sources", broken_list_sources)
    response = client.get("/sources")
    assert response.status_code == 500
    assert "logs/api.log" in response.json()["detail"]
