import os
import requests
from services.pdf_reader import extract_text
from bson.objectid import ObjectId

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


async def search_youtube_videos(pdf_id: str, db, max_results: int = 5):
    if not YOUTUBE_API_KEY:
        return []

    pdf_metadata = await db.pdfs.find_one({"_id": ObjectId(pdf_id)})
    if not pdf_metadata:
        raise Exception("PDF not found")

    pdf_content_doc = await db.pdfs_content.find_one({"_id": ObjectId(pdf_metadata["file_id"])})
    if not pdf_content_doc:
        raise Exception("PDF content not found")

    text = extract_text(pdf_content_doc["content"])
    query = " ".join(text.split()[:100])

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    videos = []
    for item in data.get("items", []):
        videos.append({
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "thumbnail": item["snippet"]["thumbnails"]["default"]["url"]
        })
    return videos
