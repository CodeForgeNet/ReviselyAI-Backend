from fastapi import APIRouter, Depends, HTTPException, Query, Request
from services.pdf_reader import extract_text
from services.quiz_generator import generate_quiz_from_text
from services.rag_engine import retrieve_top_k_if_exists
import json
from bson.objectid import ObjectId # Import ObjectId for MongoDB _id
from datetime import datetime # Import datetime for timestamps

router = APIRouter()


@router.post("/generate")
async def generate(request: Request, pdf_id: str = Query(...), mcq: int = 5, saq: int = 3, laq: int = 1):
    # Find PDF metadata in MongoDB
    pdf_metadata = await request.app.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
    if not pdf_metadata:
        raise HTTPException(status_code=404, detail="PDF not found")

    # Fetch PDF content from pdfs_content collection
    pdf_content_doc = await request.app.db.pdfs_content.find_one({"_id": ObjectId(pdf_metadata["file_id"])})
    if not pdf_content_doc:
        raise HTTPException(status_code=404, detail="PDF content not found")
    
    # Assuming extract_text can take bytes content directly or a path to a temp file
    # If not, we'd need to write the content to a temporary file and pass the path.
    text = extract_text(pdf_content_doc["content"]) # Pass bytes content

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
    
    # Store quiz in MongoDB
    quiz_doc = {
        "pdf_id": pdf_id,
        "questions": saved,
        "created_at": datetime.utcnow()
    }
    result = await request.app.db.quizzes.insert_one(quiz_doc)
    
    return {"quiz_id": str(result.inserted_id), "questions": saved}
