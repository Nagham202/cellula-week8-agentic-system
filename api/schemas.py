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
    chat_history: list[ChatMessage] = []


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    analysis: str
    from_cache: bool


class AskVoiceResponse(AskResponse):
    transcript: str


class ReportRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    analysis: str = ""
    sources: list[str] = []
    style: str | None = Field(default=None, examples=["formal, navy headings, large title"])
