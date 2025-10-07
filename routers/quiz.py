# routers/quiz.py
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from sqlalchemy.orm import Session
from models.pdf_file import PDFFile
from models.quiz import Quiz
from services.pdf_reader import extract_text
from services.quiz_generator import generate_quiz_from_text
from services.rag_engine import retrieve_top_k_if_exists
import json

router = APIRouter()


@router.post("/generate")
def generate(pdf_id: int = Query(...), mcq: int = 5, saq: int = 3, laq: int = 1, db: Session = Depends(get_db)):
    pdf = db.query(PDFFile).filter_by(id=pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    text = extract_text(pdf.path)
    # try using RAG to get context for generation (optional)
    context = None
    try:
        context = retrieve_top_k_if_exists(pdf_id, "summary", k=3)
    except Exception:
        context = None
    questions = generate_quiz_from_text(
        text, mcq=mcq, saq=saq, laq=laq, context=context)
    # if questions is raw string, wrap it
    if isinstance(questions, dict):
        saved = questions
    else:
        # fallback string
        saved = {"raw": str(questions)}
    quiz = Quiz(pdf_id=pdf.id, questions=saved)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return {"quiz_id": quiz.id, "questions": saved}
