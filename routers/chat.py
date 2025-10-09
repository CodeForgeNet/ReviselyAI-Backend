from fastapi import APIRouter, Depends, HTTPException, Request
from schemas import ChatRequest, ChatResp
from services.rag_engine import answer_with_context
from routers.auth import get_current_user
from bson.objectid import ObjectId # Import ObjectId for MongoDB _id

router = APIRouter()


@router.post("/ask", response_model=ChatResp)
async def ask(payload: ChatRequest, request: Request, user=Depends(get_current_user)):
    pdf = await request.app.db.pdfs.find_one({"_id": ObjectId(payload.pdf_id), "user_id": user.id})
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    res = answer_with_context(
        payload.pdf_id, payload.question, top_k=payload.top_k or 4)
    return {"answer": res.get("answer"), "sources": res.get("sources", [])}
