from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Response, BackgroundTasks
from datetime import datetime
from bson.objectid import ObjectId
from .auth import get_current_user
from typing import List
from pydantic import BaseModel
import os


class PDFFileBase(BaseModel):
    id: str
    title: str
    user_id: str
    is_indexed: bool
    created_at: datetime
    file_id: str

    class Config:
        json_encoders = {
            ObjectId: str
        }
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


router = APIRouter()


@router.post("/upload")
async def upload_pdf(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), current_user=Depends(get_current_user)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail="Only PDF files are allowed")

    contents = await file.read()

    pdf_content_doc = {
        "filename": file.filename,
        "content": contents,
        "mimetype": "application/pdf",
        "created_at": datetime.utcnow(),
        "user_id": current_user.id
    }
    result_content = await request.app.db.pdfs_content.insert_one(pdf_content_doc)

    file_id = str(result_content.inserted_id)

    pdf_metadata = {
        "title": file.filename,
        "user_id": current_user.id,
        "file_id": file_id,
        "created_at": datetime.utcnow(),
        "is_indexed": False
    }
    result_metadata = await request.app.db.pdfs.insert_one(pdf_metadata)

    if os.getenv("RAG_ENABLED", "true").lower() in ("1", "true", "yes"):
        from main import build_index_background
        background_tasks.add_task(
            build_index_background, str(result_metadata.inserted_id), file_id)

    return {
        "id": str(result_metadata.inserted_id),
        "title": file.filename,
        "is_indexed": False,
        "file_id": file_id,
        "created_at": pdf_metadata["created_at"],
        "user_id": current_user.id
    }


@router.get("/list", response_model=List[PDFFileBase])
async def list_pdfs(request: Request, current_user=Depends(get_current_user)):
    pdfs = []
    cursor = request.app.db.pdfs.find({"user_id": current_user.id})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id")
        pdfs.append(PDFFileBase(**doc))
    return pdfs


@router.get("/{pdf_id}", response_model=PDFFileBase)
async def get_pdf(pdf_id: str, request: Request, current_user=Depends(get_current_user)):
    try:
        pdf = await request.app.db.pdfs.find_one({"_id": ObjectId(pdf_id), "user_id": current_user.id})
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")

        pdf["id"] = str(pdf["_id"])
        pdf.pop("_id")
        return PDFFileBase(**pdf)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving PDF: {str(e)}")


@router.get("/file/{file_id}")
async def get_file(file_id: str, request: Request, current_user=Depends(get_current_user)):
    try:
        print(f"Fetching file with ID: {file_id} for user: {current_user.id}")

        try:
            file_obj_id = ObjectId(file_id)
        except Exception as e:
            print(f"Invalid file_id format: {file_id}")
            raise HTTPException(
                status_code=400, detail=f"Invalid file ID format: {str(e)}")

        file_content = await request.app.db.pdfs_content.find_one({
            "_id": file_obj_id,
            "user_id": current_user.id
        })

        if not file_content:
            print(f"File not found. ID: {file_id}, User: {current_user.id}")
            raise HTTPException(status_code=404, detail="File not found")

        print(f"File found. Size: {len(file_content['content'])} bytes")

        return Response(
            content=file_content["content"],
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{file_content.get("filename", "document.pdf")}"',
                "Content-Length": str(len(file_content["content"])),
                "Cache-Control": "max-age=3600"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error serving file: {str(e)}")


@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str, request: Request, current_user=Depends(get_current_user)):
    try:

        pdf_metadata = await request.app.db.pdfs.find_one({"_id": ObjectId(pdf_id), "user_id": current_user.id})
        if not pdf_metadata:
            raise HTTPException(status_code=404, detail="PDF not found")

        file_id = pdf_metadata["file_id"]

        await request.app.db.pdfs_content.delete_one({"_id": ObjectId(file_id)})

        await request.app.db.pdfs.delete_one({"_id": ObjectId(pdf_id)})

        return {"message": "PDF deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting PDF: {str(e)}")
