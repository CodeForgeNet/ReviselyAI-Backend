from dotenv import load_dotenv

load_dotenv()

from routers import auth
from routers import upload
from routers import quiz
from routers import progress
from routers import chat
from routers import youtube
from routers import revise_chat # Import revise_chat

# main.py
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import motor.motor_asyncio
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId # Keep ObjectId for now, might be needed for some operations

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/revisely_db") # Added default database name

# For async operations with FastAPI
async_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = async_client.get_database("revisely_db") # Explicitly get database

# For sync operations if needed (e.g., for check_db_connection)
sync_client = MongoClient(MONGODB_URI)
sync_db = sync_client.get_database("revisely_db") # Explicitly get database

# Connection check function
def check_db_connection():
    try:
        # The ismaster command is cheap and does not require auth
        sync_client.admin.command('ismaster')
        return True
    except ConnectionFailure:
        return False

from dotenv import load_dotenv

load_dotenv()

from routers import auth
from routers import upload
from routers import quiz
from routers import progress
from routers import chat
from routers import youtube
from routers import revise_chat # Import revise_chat

# main.py
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import motor.motor_asyncio
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId # Keep ObjectId for now, might be needed for some operations

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/revisely_db") # Added default database name

# For async operations with FastAPI
async_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = async_client.get_database("revisely_db") # Explicitly get database

# For sync operations if needed (e.g., for check_db_connection)
sync_client = MongoClient(MONGODB_URI)
sync_db = sync_client.get_database("revisely_db") # Explicitly get database

# Connection check function
def check_db_connection():
    try:
        # The ismaster command is cheap and does not require auth
        sync_client.admin.command('ismaster')
        return True
    except ConnectionFailure:
        return False

app = FastAPI(title="BeyondChats Backend (Full)")

# Make database available to routes
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = async_client # Store the async client
    app.db = db # Store the async database
    if not check_db_connection():
        print("Warning: MongoDB connection failed. Some features may not work.")
    else:
        print("MongoDB connected successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()


# CORS - allow local dev + your front-end domain(s)
allowed_origins = [
    "http://localhost:5173",  # Vite dev
    os.getenv("FRONTEND_URL", ""),  # set when deploying
]
# Filter out empty strings from allowed_origins
allowed_origins = [origin for origin in allowed_origins if origin]
print(f"[DEBUG] CORS allowed origins: {allowed_origins}") # Debug print

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task for RAG index building


async def build_index_background(pdf_id: str, file_id: str): # Make async
    from services.rag_engine import build_vectorstore_for_pdf
    try:
        await build_vectorstore_for_pdf(pdf_id, file_id, app.db) # Await and pass app.db
        print(f"Successfully built index for PDF {pdf_id}")
    except Exception as e:
        print(f"Failed to build index for PDF {pdf_id}: {e}")


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
app.include_router(revise_chat.router, prefix="/revisechat", tags=["revisechat"]) # Include revise_chat router


# Background task for RAG index building


async def build_index_background(pdf_id: str, file_id: str): # Make async
    from services.rag_engine import build_vectorstore_for_pdf
    try:
        await build_vectorstore_for_pdf(pdf_id, file_id, app.db) # Await and pass app.db
        print(f"Successfully built index for PDF {pdf_id}")
    except Exception as e:
        print(f"Failed to build index for PDF {pdf_id}: {e}")


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
app.include_router(revise_chat.router, prefix="/revisechat", tags=["revisechat"]) # Include revise_chat router
