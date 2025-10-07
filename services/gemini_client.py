# services/gemini_client.py
import os
import requests
from typing import Any

GEMINI_URL = os.getenv("GEMINI_API_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")


def call_gemini(prompt: str, max_tokens: int = 1024, temperature: float = 0.2) -> str:
    """
    Generic HTTP POST to your Gemini endpoint. Adapt payload shape to your endpoint if needed.
    """
    if not GEMINI_URL or not GEMINI_KEY:
        raise RuntimeError(
            "GEMINI_API_URL and GEMINI_API_KEY must be set in env")

    headers = {
        "Authorization": f"Bearer {GEMINI_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "max_output_tokens": max_tokens,
        "temperature": temperature
    }
    r = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    # parse common shapes
    if isinstance(data, dict):
        if "candidates" in data and data["candidates"]:
            return data["candidates"][0].get("content", str(data))
        if "output" in data and data["output"]:
            return data["output"][0].get("content", str(data))
    return str(data)
