from pydantic import BaseModel, Field
from typing import Any, List, Optional
from datetime import datetime
from bson import ObjectId # Import ObjectId for custom type


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema: dict):
        field_schema.update(type="string")


class TokenIn(BaseModel):
    token: str


class UploadResp(BaseModel):
    id: str = Field(alias="_id") # MongoDB _id
    title: str
    is_indexed: bool

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PDFFileBase(BaseModel):
    id: str = Field(alias="_id") # MongoDB _id
    title: str
    user_id: str
    is_indexed: bool
    created_at: datetime
    file_id: str # Link to the content document
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class GenerateQuizResp(BaseModel):
    quiz_id: str = Field(alias="_id") # MongoDB _id
    questions: Any

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ChatRequest(BaseModel):
    pdf_id: str
    question: str
    top_k: Optional[int] = 4


class ChatResp(BaseModel):
    answer: str
    sources: List[str] # Sources will be strings now


class QuizSubmit(BaseModel):
    quiz_id: str
    answers: Any  # e.g., {"mcq":[1,0,2], "saq": {...}}
