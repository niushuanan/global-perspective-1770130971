from app.core.config import settings


async def search_video(client, query: str, lang) -> dict | None:
    if settings.youtube_api_key:
        return await _search_youtube_api(client, query, lang)
    return await _search_invidious_fallback(client, query)


async def fetch_comments(client, video_id: str, lang) -> list[dict]:
    if settings.youtube_api_key:
        return await _fetch_comments_api(client, video_id)
    return await _fetch_comments_invidious_fallback(client, video_id)


async def _search_youtube_api(client, query: str, lang) -> dict | None:
    params = {
        "part": "snippet",
        "maxResults": 1,
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
        return None
    item = items[0]
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId")
    if not video_id:
        return None
    return {
        "videoId": video_id,
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


async def _fetch_comments_api(client, video_id: str) -> list[dict]:
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 5,
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
            results.append({"original": text})
    return results


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


async def _fetch_comments_invidious_fallback(client, video_id: str) -> list[dict]:
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
        for item in comments[:5]:
            content = item.get("content") or item.get("contentHtml") or ""
            if content:
                cleaned = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
                if cleaned:
                    results.append({"original": cleaned})
        return results
    return []
