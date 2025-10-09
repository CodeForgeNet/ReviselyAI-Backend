from pydantic import BaseModel, Field
from typing import Any, List, Optional, Callable # Import Callable
from datetime import datetime
from bson import ObjectId # Import ObjectId for custom type
from pydantic_core import core_schema, PydanticCustomError # Import core_schema and PydanticCustomError


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Callable[[Any], core_schema.CoreSchema]) -> core_schema.CoreSchema:
        def validate_from_str(input_value: str) -> ObjectId:
            if not ObjectId.is_valid(input_value):
                raise PydanticCustomError("invalid_object_id", "Invalid ObjectId")
            return ObjectId(input_value)

        def serialize_to_str(instance: ObjectId) -> str:
            return str(instance)

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize_to_str),
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
