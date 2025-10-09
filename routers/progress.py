from fastapi import APIRouter, Depends, HTTPException, Request
from routers.auth import get_current_user
from schemas import QuizSubmit
import math
from bson.objectid import ObjectId # Import ObjectId for MongoDB _id
from datetime import datetime # Import datetime for timestamps
from thefuzz import fuzz
from collections import defaultdict

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
    mcq_results = []
    if mcqs and "mcq" in payload.answers:
        user_answers = payload.answers.get("mcq", {})
        for i, q in enumerate(mcqs):
            total += 1
            correct_idx = q.get("answer_index")
            is_correct = str(i) in user_answers and user_answers[str(i)] == correct_idx
            if is_correct:
                score += 1
            mcq_results.append({"correct_index": correct_idx, "user_answer": user_answers.get(str(i)), "is_correct": is_correct})

    # handle saq scoring
    saqs = questions.get("saqs")
    saq_results = []
    if saqs and "saq" in payload.answers:
        user_answers = payload.answers.get("saq", {})
        for i, q in enumerate(saqs):
            total += 1
            correct_answer = q.get("answer")
            user_answer = user_answers.get(str(i), "")
            is_correct = fuzz.ratio(user_answer.lower(), correct_answer.lower()) > 80
            if is_correct:
                score += 1
            saq_results.append({"correct_answer": correct_answer, "user_answer": user_answer, "is_correct": is_correct})

    # handle laq scoring
    laqs = questions.get("laqs")
    laq_results = []
    if laqs and "laq" in payload.answers:
        user_answers = payload.answers.get("laq", {})
        for i, q in enumerate(laqs):
            total += 1
            correct_outline = " ".join(q.get("answer_outline", []))
            user_answer = user_answers.get(str(i), "")
            is_correct = fuzz.ratio(user_answer.lower(), correct_outline.lower()) > 70
            if is_correct:
                score += 1
            laq_results.append({"user_answer": user_answer, "is_correct": is_correct})
    
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
    
    return {
        "score": int(score),
        "total": int(total),
        "pct": pct,
        "results": {
            "mcq": mcq_results,
            "saq": saq_results,
            "laq": laq_results,
        }
    }

@router.get("/")
async def get_progress(request: Request, user=Depends(get_current_user)):
    all_attempts = await request.app.db.quiz_attempts.find({"user_id": user.id}).to_list(length=None)
    
    overall_total_questions = 0
    overall_correct_answers = 0
    processed_attempts = []

    for attempt in all_attempts:
        quiz_id = attempt["quiz_id"]
        quiz = await request.app.db.quizzes.find_one({"_id": ObjectId(quiz_id)})
        if not quiz:
            continue # Skip if quiz not found

        questions_data = quiz.get("questions", {})
        mcqs = questions_data.get("mcqs", [])
        saqs = questions_data.get("saqs", [])
        laqs = questions_data.get("laqs", [])

        attempt_mcq_correct = 0
        attempt_mcq_total = len(mcqs)
        if "mcq" in attempt["answers"]:
            user_mcq_answers = attempt["answers"]["mcq"]
            for i, q in enumerate(mcqs):
                if str(i) in user_mcq_answers and user_mcq_answers[str(i)] == q.get("answer_index"):
                    attempt_mcq_correct += 1
        
        attempt_saq_correct = 0
        attempt_saq_total = len(saqs)
        if "saq" in attempt["answers"]:
            user_saq_answers = attempt["answers"]["saq"]
            for i, q in enumerate(saqs):
                user_answer = user_saq_answers.get(str(i), "")
                correct_answer = q.get("answer")
                if fuzz.ratio(user_answer.lower(), correct_answer.lower()) > 80:
                    attempt_saq_correct += 1

        attempt_laq_correct = 0
        attempt_laq_total = len(laqs)
        if "laq" in attempt["answers"]:
            user_laq_answers = attempt["answers"]["laq"]
            for i, q in enumerate(laqs):
                user_answer = user_laq_answers.get(str(i), "")
                correct_outline = " ".join(q.get("answer_outline", []))
                if fuzz.ratio(user_answer.lower(), correct_outline.lower()) > 70:
                    attempt_laq_correct += 1

        overall_total_questions += (attempt_mcq_total + attempt_saq_total + attempt_laq_total)
        overall_correct_answers += (attempt_mcq_correct + attempt_saq_correct + attempt_laq_correct)

        processed_attempts.append({
            "attempt_id": str(attempt["_id"]),
            "created_at": attempt["created_at"],
            "mcq_score": f"{attempt_mcq_correct}/{attempt_mcq_total}",
            "saq_score": f"{attempt_saq_correct}/{attempt_saq_total}",
            "laq_score": f"{attempt_laq_correct}/{attempt_laq_total}",
            "overall_score": f"{attempt_mcq_correct + attempt_saq_correct + attempt_laq_correct}/{attempt_mcq_total + attempt_saq_total + attempt_laq_total}"
        })
    
    overall_percentage = (overall_correct_answers / overall_total_questions) * 100 if overall_total_questions > 0 else 0

    return {
        "overall_summary": {
            "total_questions_attempted": overall_total_questions,
            "total_correct_answers": overall_correct_answers,
            "overall_accuracy_percentage": round(overall_percentage, 2)
        },
        "attempts": processed_attempts
    }
