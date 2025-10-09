# Revisely Backend

This document outlines the setup, execution, and architecture of the Revisely backend application.

## Table of Contents

- [Setup](#setup)
- [How to Run](#how-to-run)
- [Project Architecture and Technologies](#project-architecture-and-technologies)
- [Features Implemented](#features-implemented)
- [Missing Features & Future Improvements](#missing-features--future-improvements)
- [LLM Tools Usage](#llm-tools-usage)

## Setup

### Prerequisites

- Python 3.9+
- MongoDB instance (local or cloud-hosted like MongoDB Atlas)
- Firebase Project (for authentication)
- Google Cloud Project with Gemini API enabled

### Environment Variables

Create a `.env` file in the `revisely-backend` directory with the following variables:

```
# Mongodb URL
DATABASE_URL=MongoDbUrl

# Firebase: either set path to JSON file (dev) or paste JSON content (RENDER)
# For Render: set FIREBASE_SERVICE_ACCOUNT_JSON to the full JSON content
FIREBASE_CREDENTIALS_JSON=/path/to/service-account.json
# or
FIREBASE_SERVICE_ACCOUNT_JSON=<paste-json-here>

# Gemini
GEMINI_API_URL=https://your-gemini-endpoint
GEMINI_API_KEY=your_gemini_api_key

# RAG / embeddings
RAG_ENABLED=true
EMBEDDING_MODEL=all-MiniLM-L6-v2

# YouTube (optional)
YOUTUBE_API_KEY=your_youtube_api_key

# Frontend URL (for CORS)
FRONTEND_URL=https://your-frontend.vercel.app

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Note on `FIREBASE_SERVICE_ACCOUNT_JSON`:**

- If you have the JSON content directly, paste it as a single-line string (ensure special characters are escaped if necessary, though direct pasting usually works).
- Alternatively, you can set `FIREBASE_CREDENTIALS_JSON="/path/to/your/firebase-adminsdk.json"` if you prefer to keep the JSON in a file.

### Installation

1. Navigate to the `revisely-backend` directory:
   ```bash
   cd revisely-backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

1. Ensure your `.env` file is configured and your virtual environment is activated.
2. Start the FastAPI application using Uvicorn:
   ```bash
   uvicorn main:app --reload
   ```
   The application will run on `http://127.0.0.1:8000` (or another port if configured).

## Project Architecture and Technologies

- **Framework:** FastAPI (Python)
- **Database:** MongoDB (via `motor` for async operations and `pymongo` for sync checks)
- **Authentication:** Firebase Authentication
- **PDF Processing:** `pymupdf` for PDF content extraction
- **RAG Engine:** `sentence-transformers` for embeddings, `FAISS` for vector store, `langchain` for orchestration
- **Generative AI:** Google Gemini API
- **Data Validation:** Pydantic
- **CORS:** Handled by FastAPI's `CORSMiddleware`

The project follows a modular structure with routers for different functionalities (auth, upload, quiz, chat, revise_chat, progress, youtube) and services for business logic (gemini_client, pdf_reader, quiz_generator, rag_engine, youtube_recommender).

## Features Implemented

- **User Authentication:** Firebase-based user registration and login.
- **PDF Upload & Processing:**
  - Upload PDF files.
  - Extract text content from PDFs.
  - Build vector stores (FAISS) for RAG (Retrieval Augmented Generation) based on PDF content.
- **PDF-based Chat:**
  - Ask questions about uploaded PDFs.
  - Receive answers with context from the PDF content.
- **Revise Chat (Standalone AI Chat):**
  - General conversational AI chat using Google Gemini.
  - Chat history management (create new sessions, view past sessions).
  - Markdown rendering in chat responses.
- **Quiz Generation:** Generate quizzes (MCQ, SAQ, LAQ) from PDF content.
- **Quiz Submission & Progress Tracking:**
  - Submit quiz answers.
  - Track user progress and accuracy for quizzes.
- **YouTube Integration:** (Placeholder/initial setup, actual functionality might be in `youtube_recommender.py`)
- **CORS Handling:** Configured to allow frontend access.

## Missing Features & Future Improvements

- **Robust Error Handling:** More granular error handling and user-friendly error messages.
- **Scalability for RAG:** For very large PDFs or many users, consider distributed vector stores and more advanced RAG techniques.
- **Chat History Persistence (PDF Chat):** Currently, only revise chat history is persisted. PDF chat history needs to be implemented.
- **Real-time Updates:** Implement WebSockets for real-time chat updates.
- **More Sophisticated Quiz Scoring:** Enhance SAQ/LAQ scoring beyond fuzzy matching.
- **User Interface Enhancements:** Frontend improvements for better user experience.
- **Comprehensive Testing:** Add unit and integration tests for all modules.
- **Deployment Automation:** Scripts or configurations for easier deployment to cloud platforms.
- **Security Hardening:** Review and implement additional security best practices.

## LLM Tools Usage

This project extensively uses the **Google Gemini API** for generative AI capabilities. Specifically:

- **`services/gemini_client.py`:** This module acts as the interface for interacting with the Gemini API. It sends user prompts to the `gemini-2.5-flash` model and processes the responses.
- **Purpose:**
  - **Revise Chat:** Powers the standalone conversational AI, generating responses to general user questions.
  - **Quiz Generation:** Used to generate quiz questions (MCQ, SAQ, LAQ) based on provided PDF content.
  - **RAG Engine:** While the RAG engine primarily retrieves context, Gemini is used to synthesize answers based on the retrieved context and the user's question.

**Note:** During development, `logger.debug` statements were temporarily added to `gemini_client.py` to inspect the raw API responses for debugging purposes. These have since been removed for cleaner production logs.
