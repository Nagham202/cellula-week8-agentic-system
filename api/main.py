# run from the project folder with: uvicorn api.main:app --reload

from fastapi import FastAPI

app = FastAPI(
    title="Chat with your documents API",
    description="Upload documents, ask questions about them, and get answers with sources.",
    version="1.0.0",
)


@app.get("/health")
def health():
    # TODO (your turn): return a dict with one key "status" and the value "ok"
    return None
