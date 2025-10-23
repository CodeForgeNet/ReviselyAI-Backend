from fastapi import APIRouter, Query, Request
from services.youtube_recommender import search_youtube_videos

router = APIRouter()


@router.get("/search")
async def search(request: Request, pdf_id: str = Query(...), max_results: int = 5):
    videos = await search_youtube_videos(pdf_id, request.app.db, max_results=max_results)
    return {"videos": videos}
