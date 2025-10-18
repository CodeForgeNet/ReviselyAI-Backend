import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import requests
import shutil
from bson.objectid import ObjectId
import motor.motor_asyncio
from pymongo import MongoClient
from services.gemini_client import get_gemini_response


async def build_vectorstore_for_pdf(pdf_id: str, file_id: str, db):

    temp_dir = f"temp_pdfs/{pdf_id}"
    os.makedirs(temp_dir, exist_ok=True)
    pdf_path = os.path.join(temp_dir, f"{pdf_id}.pdf")

    try:

        pdf_content_doc = await db.pdfs_content.find_one({"_id": ObjectId(file_id)})
        if not pdf_content_doc:
            raise FileNotFoundError(
                f"PDF content not found for file_id: {file_id}")

        pdf_content = pdf_content_doc["content"]

        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)

        vectorstore_path = f"vectorstores/{pdf_id}"
        vectorstore.save_local(vectorstore_path)
        print(f"Vector store for PDF {pdf_id} built and saved.")

    except Exception as e:
        print(f"Error building vector store for PDF {pdf_id}: {e}")
        raise
    finally:

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def retrieve_top_k_if_exists(pdf_id: str, query: str, k: int = 3):
    vectorstore_path = f"vectorstores/{pdf_id}"
    if not os.path.exists(vectorstore_path):
        print(
            f"Vector store not found for PDF {pdf_id}. Cannot retrieve context.")
        return []

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(
        vectorstore_path, embeddings, allow_dangerous_deserialization=True)

    docs = vectorstore.similarity_search(query, k=k)

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

    sources = []
    for doc in retrieved_docs:
        if "page" in doc["metadata"]:
            sources.append(
                f"p. {doc['metadata']['page']}: '{doc['page_content'][:100]}...'")

    return {"answer": raw_answer, "sources": sources}
