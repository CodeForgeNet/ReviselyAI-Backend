from fastapi import APIRouter, Depends, HTTPException, Request
from routers.auth import get_current_user
from schemas import QuizSubmit
import math
from bson.objectid import ObjectId # Import ObjectId for MongoDB _id
from datetime import datetime # Import datetime for timestamps

router = APIRouter()


@router.post("/submit")
async def submit_quiz(payload: QuizSubmit, request: Request, user=Depends(get_current_user)):
    # Find quiz in MongoDB
    quiz = await request.app.db.quizzes.find_one({"_id": ObjectId(payload.quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # scoring: we assume quiz.questions has 'mcqs' list with answer_index field
    questions = quiz.get("questions", {})
    score = 0
    total = 0
    
    # handle mcq scoring
    mcqs = questions.get("mcqs")
    if mcqs and "mcq" in payload.answers:
        user_answers = payload.answers.get("mcq", [])
        for i, q in enumerate(mcqs):
            total += 1
            correct_idx = q.get("answer_index")
            if i < len(user_answers) and user_answers[i] == correct_idx:
                score += 1
    
    # store attempt
    attempt_doc = {
        "quiz_id": payload.quiz_id,
        "user_id": user.id, # user.id is now a string from MongoDB _id
        "score": int(score),
        "answers": payload.answers,
        "created_at": datetime.utcnow()
    }
    await request.app.db.quiz_attempts.insert_one(attempt_doc)
    
    # update progress basic metric
    topic = f"pdf_{quiz['pdf_id']}" # Assuming quiz has pdf_id
    pct = (score/total)*100 if total > 0 else 0
    
    # Find existing progress or create new
    prog = await request.app.db.progress.find_one({"user_id": user.id, "topic": topic})
    
    if not prog:
        progress_doc = {
            "user_id": user.id,
            "topic": topic,
            "accuracy": pct,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await request.app.db.progress.insert_one(progress_doc)
    else:
        # naive average update
        new_accuracy = (prog["accuracy"] + pct) / 2
        await request.app.db.progress.update_one(
            {"_id": prog["_id"]},
            {"$set": {"accuracy": new_accuracy, "updated_at": datetime.utcnow()}}
        )
    
    return {"score": int(score), "total": int(total), "pct": pct}
