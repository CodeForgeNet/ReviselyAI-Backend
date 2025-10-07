# main.py
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import Base, engine
import models  # register models
from routers import auth, upload, quiz, progress, chat, youtube

# create tables (simple for demo; use Alembic in prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BeyondChats Backend (Full)")

# CORS - allow local dev + your front-end domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        os.getenv("FRONTEND_URL", ""),  # set when deploying
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task for RAG index building


def build_index_background(pdf_id: int, pdf_path: str):
    from services.rag_engine import build_vectorstore_for_pdf
    try:
        build_vectorstore_for_pdf(pdf_id, pdf_path)
        print(f"Successfully built index for PDF {pdf_id}")
    except Exception as e:
        print(f"Failed to build index for PDF {pdf_id}: {e}")


# mount uploads folder
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(upload.router, prefix="/files", tags=["files"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
