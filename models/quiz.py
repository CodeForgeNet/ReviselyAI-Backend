# models/quiz.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base


class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdf_files.id"))
    questions = Column(JSON)   # store structured questions/answers
    created_at = Column(DateTime, server_default=func.now())
