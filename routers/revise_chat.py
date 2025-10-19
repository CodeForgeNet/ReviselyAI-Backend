from fastapi import APIRouter, Depends, HTTPException, Request, Response
from schemas import ChatResp, ReviseChatRequestCreate, ReviseChatSession, ReviseChatMessage, ReviseChatSessionCreate
from services.gemini_client import get_gemini_response
from routers.auth import get_current_user
from typing import List, Optional
from bson.objectid import ObjectId
from datetime import datetime

router = APIRouter()


@router.get("/history", response_model=List[ReviseChatSession])
async def get_revise_chat_history(request: Request, user=Depends(get_current_user)):
    sessions = await request.app.db.revise_chat_sessions.find({"user_id": user.id}).sort("updated_at", -1).to_list(length=None)
    return sessions


@router.get("/{session_id}", response_model=ReviseChatSession)
async def get_revise_chat_session(session_id: str, request: Request, user=Depends(get_current_user)):
    session = await request.app.db.revise_chat_sessions.find_one({"_id": ObjectId(session_id), "user_id": user.id})
    if not session:
        raise HTTPException(
            status_code=404, detail="Revise Chat Session not found")
    return session


@router.post("/ask", response_model=ChatResp)
async def revise_chat_ask(payload: ReviseChatRequestCreate, request: Request, user=Depends(get_current_user)):
    user_message = ReviseChatMessage(role="user", content=payload.question)
    response_content = await get_gemini_response(payload.question)
    ai_message = ReviseChatMessage(role="assistant", content=response_content)

    if payload.session_id:

        session = await request.app.db.revise_chat_sessions.find_one({"_id": ObjectId(payload.session_id), "user_id": user.id})
        if not session:
            raise HTTPException(
                status_code=404, detail="Revise Chat Session not found")

        await request.app.db.revise_chat_sessions.update_one(
            {"_id": ObjectId(payload.session_id)},
            {
                "$push": {"messages": {"$each": [user_message.dict(), ai_message.dict()]}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        session_id = payload.session_id
    else:

        title = payload.question[:50] + \
            ("..." if len(payload.question) > 50 else "")
        new_session_data = ReviseChatSessionCreate(
            user_id=user.id,
            title=title,
            messages=[user_message, ai_message],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        result = await request.app.db.revise_chat_sessions.insert_one(new_session_data.dict())
        session_id = str(result.inserted_id)

    return {"answer": response_content, "sources": [], "session_id": session_id}


@router.delete("/{session_id}", status_code=204)
async def delete_revise_chat_session(session_id: str, request: Request, user=Depends(get_current_user)):
    print(f"Deleting session {session_id} for user {user.id}")
    result = await request.app.db.revise_chat_sessions.delete_one({"_id": ObjectId(session_id), "user_id": user.id})
    print(f"Delete result: {result.deleted_count}")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Revise Chat Session not found")
    return Response(status_code=204)
