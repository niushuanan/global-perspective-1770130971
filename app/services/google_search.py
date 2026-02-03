import urllib.parse

import feedparser

from app.core.config import settings


async def search_news(client, query: str, lang) -> list[dict]:
    if settings.google_cse_api_key and settings.google_cse_id:
        return await _search_cse(client, query, lang)
    return await _search_google_news_rss(client, query, lang)


async def _search_cse(client, query: str, lang) -> list[dict]:
    params = {
        "key": settings.google_cse_api_key,
        "cx": settings.google_cse_id,
        "q": query,
        "num": 5,
        "lr": lang.google_lr,
        "gl": lang.google_gl,
    }
    response = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    results = []
    for item in items:
        link = item.get("link", "")
        if _is_ad_link(link):
            continue
        results.append(
            {
                "title": item.get("title", ""),
                "link": link,
                "source": item.get("displayLink", ""),
            }
        )
    return results


async def _search_google_news_rss(client, query: str, lang) -> list[dict]:
    encoded = urllib.parse.quote(query)
    url = (
        f"https://news.google.com/rss/search?q={encoded}"
        f"&hl={lang.google_hl}&gl={lang.google_gl}&ceid={lang.google_ceid}"
    )
    response = await client.get(url)
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    results = []
    for entry in feed.entries[:8]:
        link = entry.get("link", "")
        if not link or _is_ad_link(link):
            continue
        source = entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else ""
        results.append({"title": entry.get("title", ""), "link": link, "source": source})
    return results


def _is_ad_link(url: str) -> bool:
    lowered = url.lower()
    return any(token in lowered for token in ["googleadservices", "doubleclick", "adservice"]) 
