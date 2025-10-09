from pydantic import BaseModel, Field
from typing import Any, List, Optional, Callable # Import Callable
from datetime import datetime
from bson import ObjectId # Import ObjectId for custom type
from pydantic_core import core_schema # Import core_schema


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if v is None: # Allow None values
            return None
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: core_schema.CoreSchema, handler: Callable[[Any], core_schema.CoreSchema]) -> core_schema.CoreSchema:
        # This method is called by Pydantic v2 to get the JSON schema for the type
        # We want to represent ObjectId as a string in the JSON schema
        return core_schema.json_or_ser_pydantic_validate_json_fallback(
            core_schema.str_schema(),
            core_schema.is_instance_schema(ObjectId),
            serialization=core_schema.to_string_ser_schema(),
        )


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


class ReviseChatRequestCreate(BaseModel):
    question: str
    session_id: Optional[str] = None # Add session_id for continuing conversations


class ReviseChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReviseChatSessionCreate(BaseModel):
    user_id: str
    title: str
    messages: List[ReviseChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReviseChatSession(BaseModel):
    id: PyObjectId = Field(alias="_id") # id is required for existing sessions
    user_id: str
    title: str
    messages: List[ReviseChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class QuizSubmit(BaseModel):
    quiz_id: str
    answers: Any  # e.g., {"mcq":[1,0,2], "saq": {...}}
