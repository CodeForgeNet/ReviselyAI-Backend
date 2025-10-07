# routers/upload.py
import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from database import get_db
from sqlalchemy.orm import Session
from models.pdf_file import PDFFile
from services.pdf_reader import extract_text
from routers.auth import get_current_user
from typing import Dict
from services.cloudinary_storage import upload_to_cloudinary

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=Dict)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    # Save locally first (needed for processing)
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Create a unique public_id using user ID and filename
    public_id = f"{current_user.id}/{file.filename}"

    # Try to upload to Cloudinary if configured
    cloudinary_url = upload_to_cloudinary(save_path, public_id)

    # Store the Cloudinary URL in the database if available
    pdf_row = PDFFile(
        filename=file.filename,
        path=cloudinary_url if cloudinary_url else save_path,
        user_id=current_user.id
    )
    db.add(pdf_row)
    db.commit()
    db.refresh(pdf_row)

    # Build RAG index as a background task
    if os.getenv("RAG_ENABLED", "true").lower() in ("1", "true", "yes"):
        from main import build_index_background
        background_tasks.add_task(
            build_index_background, pdf_row.id, save_path)

    return {"id": pdf_row.id, "filename": pdf_row.filename}
