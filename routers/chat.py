# routers/chat.py
from fastapi import APIRouter, Depends, HTTPException
from schemas import ChatRequest, ChatResp
from services.rag_engine import answer_with_context
from database import get_db
from sqlalchemy.orm import Session
from models.pdf_file import PDFFile
from routers.auth import get_current_user

router = APIRouter()


@router.post("/ask", response_model=ChatResp)
def ask(payload: ChatRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    pdf = db.query(PDFFile).filter_by(id=payload.pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    res = answer_with_context(
        payload.pdf_id, payload.question, top_k=payload.top_k or 4)
    return {"answer": res.get("answer"), "sources": res.get("sources", [])}
