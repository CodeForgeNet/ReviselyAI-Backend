import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import requests
import shutil
from bson.objectid import ObjectId
import motor.motor_asyncio  # Import motor for async client
from pymongo import MongoClient  # Import MongoClient for sync client if needed
from services.gemini_client import get_gemini_response # Import get_gemini_response for answer_with_context

# pdf_id is now str, file_id is str
async def build_vectorstore_for_pdf(pdf_id: str, file_id: str, db):
    # Create a temporary directory for the PDF
    temp_dir = f"temp_pdfs/{pdf_id}"
    os.makedirs(temp_dir, exist_ok=True)
    pdf_path = os.path.join(temp_dir, f"{pdf_id}.pdf")

    try:
        # Fetch the PDF content from MongoDB
        pdf_content_doc = await db.pdfs_content.find_one({"_id": ObjectId(file_id)})
        if not pdf_content_doc:
            raise FileNotFoundError(f"PDF content not found for file_id: {file_id}")
        
        pdf_content = pdf_content_doc["content"]

        # Write content to a temporary file
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

        # Load and split the PDF
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)

        # Create embeddings and vector store
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)

        # Save the vector store
        vectorstore_path = f"vectorstores/{pdf_id}"
        vectorstore.save_local(vectorstore_path)
        print(f"Vector store for PDF {pdf_id} built and saved.")

    except Exception as e:
        print(f"Error building vector store for PDF {pdf_id}: {e}")
        raise
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def retrieve_top_k_if_exists(pdf_id: str, query: str, k: int = 3):
    vectorstore_path = f"vectorstores/{pdf_id}"
    if not os.path.exists(vectorstore_path):
        print(f"Vector store not found for PDF {pdf_id}. Cannot retrieve context.")
        return [] # Return empty list if no vector store

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(vectorstore_path, embeddings, allow_dangerous_deserialization=True)
    
    docs = vectorstore.similarity_search(query, k=k)
    
    # Return list of dicts with page_content and metadata
    return [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in docs]


async def answer_with_context(pdf_id: str, question: str, top_k: int = 4):
    retrieved_docs = retrieve_top_k_if_exists(pdf_id, question, k=top_k)
    
    if not retrieved_docs:
        return {"answer": "I could not find relevant information in the document.", "sources": []}

    context_text = "\n\n".join([doc["page_content"] for doc in retrieved_docs])
    
    prompt = f"""
    You are a helpful assistant that answers questions based on the provided context.
    If the answer is not in the context, politely state that you don't have enough information.
    
    Context:
    {context_text}
    
    Question: {question}
    
    Provide a concise answer. If applicable, cite the source page numbers from the context.
    Example citation: (p. 23)
    """
    
    raw_answer = await get_gemini_response(prompt, max_tokens=500)
    
    # Extract sources from retrieved_docs for citation
    sources = []
    for doc in retrieved_docs:
        if "page" in doc["metadata"]:
            sources.append(f"p. {doc['metadata']['page']}: '{doc['page_content'][:100]}...'") # Snippet of 100 chars
    
    return {"answer": raw_answer, "sources": sources}
