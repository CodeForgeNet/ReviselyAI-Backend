from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Response
from datetime import datetime
from bson.objectid import ObjectId
from .auth import get_current_user
from typing import List # Import List for type hinting
from pydantic import BaseModel # Import BaseModel for schema definition
import os # Import os for os.getenv

# Define a simple schema for PDF metadata for now
class PDFFileBase(BaseModel):
    id: str
    title: str
    user_id: str
    is_indexed: bool
    created_at: datetime

    class Config:
        json_encoders = {
            ObjectId: str
        }
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


router = APIRouter()

@router.post("/upload")
async def upload_pdf(request: Request, file: UploadFile = File(...), current_user = Depends(get_current_user)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    contents = await file.read()
    
    # Store PDF content in a separate collection
    pdf_content_doc = {
        "filename": file.filename,
        "content": contents,
        "mimetype": "application/pdf",
        "created_at": datetime.utcnow(),
        "user_id": current_user.id
    }
    result_content = await request.app.db.pdfs_content.insert_one(pdf_content_doc)
    file_id = str(result_content.inserted_id) # Use the _id of the content document as file_id
    
    # Store PDF metadata
    pdf_metadata = {
        "title": file.filename,
        "user_id": current_user.id,
        "file_id": file_id, # Link to the content document
        "created_at": datetime.utcnow(),
        "is_indexed": False
    }
    result_metadata = await request.app.db.pdfs.insert_one(pdf_metadata)
    
    # Start indexing in background task
    if os.getenv("RAG_ENABLED", "true").lower() in ("1", "true", "yes"):
        from main import build_index_background
        request.app.background_tasks.add_task(
            build_index_background, str(result_metadata.inserted_id), file_id)
    
    return {"id": str(result_metadata.inserted_id), "title": file.filename, "is_indexed": False}

@router.get("/list", response_model=List[PDFFileBase])
async def list_pdfs(request: Request, current_user = Depends(get_current_user)):
    pdfs = []
    cursor = request.app.db.pdfs.find({"user_id": current_user.id})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id")
        pdfs.append(PDFFileBase(**doc)) # Convert to Pydantic model
    return pdfs

@router.get("/{pdf_id}", response_model=List[PDFFileBase])
async def get_pdf(pdf_id: str, request: Request, current_user = Depends(get_current_user)):
    try:
        pdf = await request.app.db.pdfs.find_one({"_id": ObjectId(pdf_id), "user_id": current_user.id})
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        pdf["id"] = str(pdf["_id"])
        pdf.pop("_id")
        return PDFFileBase(**pdf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving PDF: {str(e)}")

@router.get("/file/{file_id}")
async def get_file(file_id: str, request: Request, current_user = Depends(get_current_user)):
    # Find file content in MongoDB
    file_content = await request.app.db.pdfs_content.find_one({"_id": ObjectId(file_id), "user_id": current_user.id})
    
    if not file_content:
        raise HTTPException(status_code=404, detail="File not found")
    
    return Response(
        content=file_content["content"],
        media_type=file_content["mimetype"]
    )

@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str, request: Request, current_user = Depends(get_current_user)):
    try:
        # Find the PDF metadata first
        pdf_metadata = await request.app.db.pdfs.find_one({"_id": ObjectId(pdf_id), "user_id": current_user.id})
        if not pdf_metadata:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        file_id = pdf_metadata["file_id"]
        
        # Delete PDF content
        await request.app.db.pdfs_content.delete_one({"_id": ObjectId(file_id)})
        
        # Delete PDF metadata
        await request.app.db.pdfs.delete_one({"_id": ObjectId(pdf_id)})
        
        return {"message": "PDF deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting PDF: {str(e)}")