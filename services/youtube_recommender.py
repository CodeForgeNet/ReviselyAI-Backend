import os
import requests

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def search_youtube_videos(query: str, max_results: int = 5):
    if not YOUTUBE_API_KEY:
        return []
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
