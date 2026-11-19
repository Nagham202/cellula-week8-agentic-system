# the shapes of the data each endpoint sends back, shown on the /docs page

from typing import Literal

from pydantic import BaseModel, Field


class UploadResult(BaseModel):
    filename: str
    chunks: int


class SourceInfo(BaseModel):
    name: str
    chunks: int


class SourceList(BaseModel):
    sources: list[SourceInfo]
    total_chunks: int


class Message(BaseModel):
    message: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000, examples=["What does error E31 mean?"])
    # the earlier messages of this conversation, oldest first, so follow-ups like "How do I fix it?" work
    chat_history: list[ChatMessage] = []


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    # what the Analyst found, the client sends it back to /report
    analysis: str
    from_cache: bool


# the same fields as AskResponse, plus the text heard in the audio
class AskVoiceResponse(AskResponse):
    transcript: str


class ReportRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    analysis: str = ""
    sources: list[str] = []
    # design wishes in plain words, the report agent turns them into fonts, sizes and colors
    style: str | None = Field(default=None, examples=["formal, navy headings, large title"])
