from datetime import datetime, timezone
from math import log10

from app.core.config import settings


async def search_videos(client, query: str, lang, limit: int = 2) -> list[dict]:
    if settings.youtube_api_key:
        return await _search_youtube_api(client, query, lang, limit=limit)
    fallback = await _search_invidious_fallback(client, query)
    return [fallback] if fallback else []


async def search_video(client, query: str, lang) -> dict | None:
    videos = await search_videos(client, query, lang, limit=1)
    return videos[0] if videos else None


async def fetch_comments(client, video_id: str, lang, limit: int = 10) -> list[dict]:
    if settings.youtube_api_key:
        return await _fetch_comments_api(client, video_id, limit=limit)
    return await _fetch_comments_invidious_fallback(client, video_id, limit=limit)


async def _search_youtube_api(client, query: str, lang, limit: int = 2) -> list[dict]:
    params = {
        "part": "snippet",
        "maxResults": 10,
        "q": query,
        "type": "video",
        "order": "relevance",
        "relevanceLanguage": lang.youtube_lang,
        "regionCode": lang.youtube_region,
        "key": settings.youtube_api_key,
    }
    response = await client.get("https://www.googleapis.com/youtube/v3/search", params=params)
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    if not items:
        return []

    ranked_ids = []
    for index, item in enumerate(items):
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            ranked_ids.append((video_id, index))

    if not ranked_ids:
        return []

    video_ids = ",".join([vid for vid, _ in ranked_ids])
    stats = await _fetch_video_stats(client, video_ids)

    candidates = []
    view_logs = []
    for video_id, rank in ranked_ids:
        info = stats.get(video_id, {})
        snippet = info.get("snippet", {})
        statistics = info.get("statistics", {})
        published_at = snippet.get("publishedAt")
        view_count = int(statistics.get("viewCount", 0) or 0)
        comment_count = int(statistics.get("commentCount", 0) or 0)
        view_log = log10(view_count + 1)
        view_logs.append(view_log)
        candidates.append(
            {
                "videoId": video_id,
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "publishedAt": published_at or "",
                "viewCount": view_count,
                "commentCount": comment_count,
                "rank": rank,
                "viewLog": view_log,
            }
        )

    max_view_log = max(view_logs) if view_logs else 0.0
    for item in candidates:
        item["score"] = _score_video(
            item["viewLog"],
            max_view_log,
            item.get("publishedAt"),
            item.get("rank", 0),
        )
        if item.get("commentCount", 0) > 0:
            item["score"] += 0.05

    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    return candidates[:limit]


async def _fetch_comments_api(client, video_id: str, limit: int = 10) -> list[dict]:
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 100,
        "order": "relevance",
        "textFormat": "plainText",
        "key": settings.youtube_api_key,
    }
    response = await client.get("https://www.googleapis.com/youtube/v3/commentThreads", params=params)
    if response.status_code == 403:
        return []
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    results = []
    for item in items:
        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        text = snippet.get("textDisplay") or snippet.get("textOriginal")
        if text:
            results.append({"original": text, "likeCount": int(snippet.get("likeCount", 0) or 0)})
    results.sort(key=lambda x: x.get("likeCount", 0), reverse=True)
    return results[:limit]


async def _search_invidious_fallback(client, query: str) -> dict | None:
    params = {"q": query, "type": "video", "sort_by": "relevance"}
    last_error = None
    for base_url in settings.invidious_instances:
        try:
            response = await client.get(f"{base_url.rstrip('/')}/api/v1/search", params=params)
            if response.status_code >= 400:
                last_error = response.status_code
                continue
            data = response.json()
            if not data:
                continue
            item = data[0]
            video_id = item.get("videoId")
            if not video_id:
                continue
            return {
                "videoId": video_id,
                "title": item.get("title", ""),
                "channel": item.get("author", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        except Exception as exc:  # pragma: no cover - best effort fallback
            last_error = exc
            continue
    if last_error:
        raise RuntimeError("Invidious fallback failed")
    return None


async def _fetch_comments_invidious_fallback(client, video_id: str, limit: int = 10) -> list[dict]:
    from bs4 import BeautifulSoup
    for base_url in settings.invidious_instances:
        response = await client.get(
            f"{base_url.rstrip('/')}/api/v1/comments/{video_id}",
            params={"sort_by": "top"},
        )
        if response.status_code >= 400:
            continue
        data = response.json()
        comments = data.get("comments", [])
        results = []
        for item in comments[:limit]:
            content = item.get("content") or item.get("contentHtml") or ""
            if content:
                cleaned = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
                if cleaned:
                    results.append({"original": cleaned, "likeCount": int(item.get("likeCount", 0) or 0)})
        results.sort(key=lambda x: x.get("likeCount", 0), reverse=True)
        return results[:limit]
    return []


async def _fetch_video_stats(client, video_ids: str) -> dict:
    params = {
        "part": "snippet,statistics",
        "id": video_ids,
        "key": settings.youtube_api_key,
    }
    response = await client.get("https://www.googleapis.com/youtube/v3/videos", params=params)
    if response.status_code >= 400:
        return {}
    data = response.json()
    results = {}
    for item in data.get("items", []):
        results[item.get("id")] = item
    return results


def _score_video(view_log: float, max_view_log: float, published_at: str | None, rank: int) -> float:
    view_score = (view_log / max_view_log) if max_view_log > 0 else 0.0
    recency_score = 0.0
    if published_at:
        try:
            published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - published).days
            if days < 0:
                days = 0
            recency_score = max(0.0, 1.0 - min(days, 365) / 365)
        except ValueError:
            recency_score = 0.0
    relevance_score = 1.0 / (rank + 1)
    return view_score * 0.35 + recency_score * 0.25 + relevance_score * 0.4
