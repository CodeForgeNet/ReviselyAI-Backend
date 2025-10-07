# services/rag_engine.py
import os
import pickle
import numpy as np
from typing import List, Dict, Any
from services.pdf_reader import extract_pages, chunk_pages_with_meta
from sentence_transformers import SentenceTransformer
import faiss

VECTOR_DIR = "vectorstores"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
os.makedirs(VECTOR_DIR, exist_ok=True)

# Lazy-load model
_embedding_model = None


def _get_embedder():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def build_vectorstore_for_pdf(pdf_id: int, pdf_path: str):
    pages = extract_pages(pdf_path)
    docs = chunk_pages_with_meta(pages, chunk_size=2000, overlap=200)
    texts = [d["text"] for d in docs]
    model = _get_embedder()
    embeddings = model.encode(
        texts, convert_to_numpy=True, show_progress_bar=True)
    # normalize for cosine-sim using inner product
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    idx_path = os.path.join(VECTOR_DIR, f"{pdf_id}.index.faiss")
    meta_path = os.path.join(VECTOR_DIR, f"{pdf_id}.meta.pkl")
    faiss.write_index(index, idx_path)
    with open(meta_path, "wb") as f:
        pickle.dump(docs, f)
    return {"index_path": idx_path, "meta_path": meta_path, "count": len(docs)}


def _load_index_and_meta(pdf_id: int):
    idx_path = os.path.join(VECTOR_DIR, f"{pdf_id}.index.faiss")
    meta_path = os.path.join(VECTOR_DIR, f"{pdf_id}.meta.pkl")
    if not os.path.exists(idx_path) or not os.path.exists(meta_path):
        return None, None
    index = faiss.read_index(idx_path)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
    return index, meta


def retrieve_top_k(pdf_id: int, query: str, k: int = 4):
    index, meta = _load_index_and_meta(pdf_id)
    if index is None:
        return []
    model = _get_embedder()
    q_emb = model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, k)
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < 0:
            continue
        item = meta[idx].copy()
        item["score"] = float(score)
        results.append(item)
    return results


def retrieve_top_k_if_exists(pdf_id: int, query: str, k: int = 4):
    # wrapper used by quiz generator - returns concatenated context or None
    res = retrieve_top_k(pdf_id, query, k=k)
    if not res:
        return None
    ctx = []
    for r in res:
        # attach page info for citation
        ctx.append(
            f"(p{','.join(map(str, r.get('pages', [])))}): {r['preview']}")
    return "\n\n".join(ctx)


def answer_with_context(pdf_id: int, question: str, top_k: int = 4):
    """
    Retrieve relevant chunks and create an answer using Gemini.
    Returns dict: {answer, sources: [{page, preview, score}], raw_model_output}
    """
    from services.gemini_client import call_gemini

    results = retrieve_top_k(pdf_id, question, k=top_k)
    if not results:
        # fallback: ask the model directly without context
        raw = call_gemini(f"Answer this question:\n{question}", max_tokens=600)
        return {"answer": raw, "sources": []}

    # Build context string
    context = ""
    for r in results:
        pages = ",".join(map(str, r.get("pages", [])))
        context += f"[p{pages}] {r['text']}\n\n"

    prompt = (
        "You are a helpful teacher. Use the context below (which comes from the student's textbook) to answer the question.\n"
        "When you use information from the context, add a citation like (pX) next to the sentence. If answer cannot be found, say 'Not in provided textbook'.\n\n"
        "Context:\n" + context + "\n\nQuestion:\n" + question +
        "\n\nAnswer clearly and include short citations and, if possible, a 1-2 line quote from the context."
    )

    raw = call_gemini(prompt, max_tokens=800)
    sources = [{"pages": r.get("pages"), "preview": r.get(
        "preview"), "score": r.get("score")} for r in results]
    return {"answer": raw, "sources": sources, "raw": raw}
