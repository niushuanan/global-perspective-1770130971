import urllib.parse

from app.core.config import settings


async def search_news(client, query: str, lang) -> list[dict]:
    results = await _search_gdelt(client, query, lang)
    if results:
        return results
    return await _search_google_news_rss(client, query, lang)


async def _search_gdelt(client, query: str, lang) -> list[dict]:
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": _build_gdelt_query(query, lang.gdelt_sourcelang),
        "mode": "ArtList",
        "format": "json",
        "maxrecords": 15,
        "sort": "DateDesc",
        "timespan": settings.gdelt_timespan,
    }
    response = await client.get(base_url, params=params)
    if response.status_code >= 400:
        return []
    data = response.json()
    articles = data.get("articles", []) if isinstance(data, dict) else []
    results = [_gdelt_article_to_result(item) for item in articles if item.get("url")]
    if results:
        return results

    # Fallback: relax language filter if no results found
    params["query"] = query
    response = await client.get(base_url, params=params)
    if response.status_code >= 400:
        return []
    data = response.json()
    articles = data.get("articles", []) if isinstance(data, dict) else []
    filtered = []
    for item in articles:
        if not item.get("url"):
            continue
        if item.get("language", "").lower().startswith(lang.key):
            filtered.append(_gdelt_article_to_result(item))
    return filtered or [_gdelt_article_to_result(item) for item in articles[:6] if item.get("url")]


def _gdelt_article_to_result(item: dict) -> dict:
    return {
        "title": item.get("title", ""),
        "link": item.get("url", ""),
        "source": item.get("domain", ""),
        "language": item.get("language", ""),
        "seendate": item.get("seendate", ""),
    }


def _build_gdelt_query(query: str, sourcelang: str) -> str:
    query = query.strip()
    if not query:
        return ""
    if sourcelang:
        return f"({query}) sourcelang:{sourcelang}"
    return query


async def _search_google_news_rss(client, query: str, lang) -> list[dict]:
    import feedparser
    encoded = urllib.parse.quote(query)
    url = (
        f"https://news.google.com/rss/search?q={encoded}"
        f"&hl={lang.google_hl}&gl={lang.google_gl}&ceid={lang.google_ceid}"
    )
    response = await client.get(url)
    if response.status_code >= 400:
        return []
    feed = feedparser.parse(response.text)
    results = []
    for entry in feed.entries[:8]:
        link = entry.get("link", "")
        if not link:
            continue
        source = entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else ""
        results.append({"title": entry.get("title", ""), "link": link, "source": source})
    return results
