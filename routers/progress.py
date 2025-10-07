# routers/progress.py
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt
from models.progress import Progress
from routers.auth import get_current_user
from schemas import QuizSubmit
import math

router = APIRouter()


@router.post("/submit")
def submit_quiz(payload: QuizSubmit, db: Session = Depends(get_db), user=Depends(get_current_user)):
    quiz = db.query(Quiz).filter_by(id=payload.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    # scoring: we assume quiz.questions has 'mcqs' list with answer_index field
    questions = quiz.questions
    score = 0
    total = 0
    # handle mcq scoring
    mcqs = questions.get("mcqs") if isinstance(questions, dict) else None
    if mcqs and "mcq" in payload.answers:
        user_answers = payload.answers.get("mcq", [])
        for i, q in enumerate(mcqs):
            total += 1
            correct_idx = q.get("answer_index")
            if i < len(user_answers) and user_answers[i] == correct_idx:
                score += 1
    # store attempt
    attempt = QuizAttempt(quiz_id=payload.quiz_id, user_id=user.id, score=int(
        score), answers=payload.answers)
    db.add(attempt)
    db.commit()
    # update progress basic metric
    topic = f"pdf_{quiz.pdf_id}"
    pct = (score/total)*100 if total > 0 else 0
    prog = db.query(Progress).filter_by(user_id=user.id, topic=topic).first()
    if not prog:
        prog = Progress(user_id=user.id, topic=topic, accuracy=pct)
        db.add(prog)
    else:
        # naive average update
        prog.accuracy = (prog.accuracy + pct) / 2
    db.commit()
    return {"score": int(score), "total": int(total), "pct": pct}
