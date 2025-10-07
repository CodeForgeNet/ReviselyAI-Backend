# services/pdf_reader.py
import fitz  # PyMuPDF
from typing import List, Dict


def extract_text(path: str) -> str:
    # Return whole text (simple)
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    return "\n".join(texts)


def extract_pages(path: str) -> List[Dict]:
    """
    Return a list of dicts: [{ "page_no": 1, "text": "..." }, ...]
    """
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc, start=1):
        t = page.get_text()
        pages.append({"page_no": i, "text": t})
    return pages


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200):
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def chunk_pages_with_meta(pages, chunk_size=2000, overlap=200):
    """
    Make chunks across pages but keep a mapping to page numbers (we keep page boundaries).
    Returns list of dict {text, pages: [list of pages included], preview}
    """
    out = []
    for p in pages:
        text = p["text"].strip()
        if not text:
            continue
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for i, c in enumerate(chunks):
            out.append({
                "text": c,
                "pages": [p["page_no"]],
                "preview": c[:300]
            })
    return out
