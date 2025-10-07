# schemas.py
from pydantic import BaseModel
from typing import Any, List, Optional


class TokenIn(BaseModel):
    token: str


class UploadResp(BaseModel):
    id: int
    filename: str


class GenerateQuizResp(BaseModel):
    quiz_id: int
    questions: Any


class ChatRequest(BaseModel):
    pdf_id: int
    question: str
    top_k: Optional[int] = 4


class ChatResp(BaseModel):
    answer: str
    sources: List[Any]


class QuizSubmit(BaseModel):
    quiz_id: int
    answers: Any  # e.g., {"mcq":[1,0,2], "saq": {...}}
