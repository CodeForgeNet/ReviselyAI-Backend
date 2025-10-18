from dotenv import load_dotenv

load_dotenv()

from routers import auth, upload, quiz, progress, chat, youtube, revise_chat
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/revisely_db")

async_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = async_client.get_database("revisely_db")

sync_client = MongoClient(MONGODB_URI)
sync_db = sync_client.get_database("revisely_db")

def check_db_connection():
    try:
        sync_client.admin.command('ismaster')
        return True
    except ConnectionFailure:
        return False

app = FastAPI(title="BeyondChats Backend (Full)")

@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = async_client
    app.db = db
    if not check_db_connection():
        print("Warning: MongoDB connection failed. Some features may not work.")
    else:
        print("MongoDB connected successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

allowed_origins = [
    "http://localhost:5173",
    os.getenv("FRONTEND_URL", ""),
]
allowed_origins = [origin for origin in allowed_origins if origin]
print(f"[DEBUG] CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def build_index_background(pdf_id: str, file_id: str):
    from services.rag_engine import build_vectorstore_for_pdf
    try:
        await build_vectorstore_for_pdf(pdf_id, file_id, app.db)
        print(f"Successfully built index for PDF {pdf_id}")
    except Exception as e:
        print(f"Failed to build index for PDF {pdf_id}: {e}")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
app.include_router(revise_chat.router, prefix="/revise-chat", tags=["revise-chat"])
