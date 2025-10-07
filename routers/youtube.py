# routers/youtube.py
from fastapi import APIRouter, Query
from services.youtube_recommender import search_youtube_videos

router = APIRouter()


@router.get("/search")
def search(q: str = Query(...), max_results: int = 5):
    return {"videos": search_youtube_videos(q, max_results=max_results)}
