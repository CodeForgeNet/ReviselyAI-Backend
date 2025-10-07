# services/quiz_generator.py
import json
from services.gemini_client import call_gemini
from typing import Any, Optional
from services.rag_engine import retrieve_top_k_if_exists


def generate_quiz_from_text(text: str, mcq: int = 5, saq: int = 3, laq: int = 1, context: Optional[str] = None) -> Any:
    """
    If context provided (from RAG), include it to improve quiz quality.
    Returns raw JSON string (prefer returning json, but depends on model).
    """
    truncated = text[:3000] if text else ""
    prompt = "You are an exam generator. From the textbook text below create:\n"
    prompt += f"- {mcq} MCQs (each with 4 options). Mark the correct option and give a short 1-2 line explanation.\n"
    prompt += f"- {saq} short-answer questions with short answers.\n"
    prompt += f"- {laq} long-answer questions with answer outlines.\n\n"
    if context:
        prompt += f"Use the following supporting context from the textbook when relevant:\n{context}\n\n"
    prompt += f"Text:\n{truncated}\n\nOutput strictly as JSON with keys: mcqs, saqs, laqs. Each mcq: question, options[], answer_index, explanation.\n"
    raw = call_gemini(prompt, max_tokens=1200)
    # Try to parse JSON - if model returned JSON string
    try:
        parsed = json.loads(raw)
        return parsed
    except Exception:
        # fallback: return raw so caller can display raw text
        return {"raw": raw}
