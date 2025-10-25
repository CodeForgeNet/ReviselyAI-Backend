import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import Pinecone
import requests
import shutil
from bson.objectid import ObjectId
import motor.motor_asyncio
from pymongo import MongoClient
from services.gemini_client import get_gemini_response
from services.pinecone_client import get_pinecone_index, REVISELY_INDEX_NAME


async def build_vectorstore_for_pdf(pdf_id: str, file_id: str, db):
    print(
        f"Starting to build vector store for PDF {pdf_id} with file_id {file_id}")
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

        dimension = 384
        pinecone_index = get_pinecone_index(dimension)

        # Generate embeddings for the texts
        vectors = embeddings.embed_documents([t.page_content for t in texts])

        # Prepare data for upsert
        upsert_data = []
        for i, text in enumerate(texts):
            upsert_data.append({
                "id": f"{pdf_id}-{i}",  # Unique ID for each vector
                "values": vectors[i],
                "metadata": {"page_content": text.page_content, **text.metadata}
            })

    except Exception as e:

        raise
    finally:

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def retrieve_top_k_if_exists(pdf_id: str, query: str, k: int = 3):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2")

    try:

        # Get the Pinecone index object
        # Dimension must match embedding model
        pinecone_index = get_pinecone_index(dimension=384)

        # Generate embedding for the query
        query_embedding = embeddings.embed_query(query)

        # Perform a raw query on the Pinecone index
        query_results = pinecone_index.query(
            vector=query_embedding,
            top_k=k,
            namespace=str(pdf_id),
            include_metadata=True
        )

        docs = []
        for match in query_results.matches:
            docs.append(
                {"page_content": match.metadata['page_content'], "metadata": match.metadata})

        return docs
    except Exception as e:
        return []


async def answer_with_context(pdf_id: str, question: str, top_k: int = 4):
    retrieved_docs = retrieve_top_k_if_exists(pdf_id, question, k=top_k)

    if not retrieved_docs:
        # If no context is found, ask Gemini for a general answer
        prompt = f"Please provide a general answer to the following question: {question}"
        general_answer = await get_gemini_response(prompt, max_tokens=1024)
        return {"answer": general_answer, "sources": []}

    context_text = "\n\n".join([doc["page_content"] for doc in retrieved_docs])

    # If context is found, use a more flexible prompt
    prompt = f"""
    You are a helpful assistant. Answer the following question based on the provided context.
    If the answer is not explicitly in the context, use your general knowledge to answer but indicate that the information is not from the document.
    
    Context:
    {context_text}
    
    Question: {question}
    
    Provide a concise answer. If the answer is from the context, cite the source page numbers.
    Example citation: (p. 23)
    """

    raw_answer = await get_gemini_response(prompt, max_tokens=1024)

    sources = []
    for doc in retrieved_docs:
        if "page" in doc["metadata"]:
            sources.append(
                f"p. {doc['metadata']['page']}: '{doc['page_content'][:100]}...'"
            )

    return {"answer": raw_answer, "sources": sources}
