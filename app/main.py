import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.config import settings
from app.core.constants import LANGUAGES
from app.services.http_client import get_client
from app.services.news_extract import extract_article
from app.services.google_search import search_news
from app.services.summarize import (
    summarize_article,
    summarize_comments_overview,
    summarize_news_overview,
)
from app.services.translate import translate_text
from app.services.utils import clip_text
from app.services.youtube import fetch_comments, search_video

app = FastAPI(title="Global Perspective Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


class QueryRequest(BaseModel):
    query: str


class SummaryRequest(BaseModel):
    query: str
    items: list[dict[str, Any]]


@app.get("/")
async def root():
    return FileResponse("app/static/index.html")


@app.post("/api/video")
async def analyze_video(request: QueryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    async with get_client() as client:
        tasks = [fetch_video_for_lang(client, lang, query) for lang in LANGUAGES]
        results = await asyncio.gather(*tasks)

    return {"query": query, "items": results}


@app.post("/api/news")
async def analyze_news(request: QueryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    async with get_client() as client:
        tasks = [fetch_news_for_lang(client, lang, query) for lang in LANGUAGES]
        results = await asyncio.gather(*tasks)

    return {"query": query, "items": results}


@app.post("/api/summary/comments")
async def summarize_comments(request: SummaryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    payload = []
    for item in request.items:
        label = item.get("label", "")
        comments = item.get("comments", [])
        if not comments:
            continue
        joined = " / ".join([c.get("original", "") for c in comments if c.get("original")])
        if joined:
            payload.append(f"{label}: {joined}")

    if not payload:
        raise HTTPException(status_code=400, detail="No comments provided")

    async with get_client() as client:
        summary = await summarize_comments_overview(client, query, "\n".join(payload))

    return {"summary": summary}


@app.post("/api/summary/news")
async def summarize_news(request: SummaryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    payload = []
    for item in request.items:
        label = item.get("label", "")
        summary = item.get("summary", "")
        if summary:
            payload.append(f"{label}: {summary}")

    if not payload:
        raise HTTPException(status_code=400, detail="No summaries provided")

    async with get_client() as client:
        summary = await summarize_news_overview(client, query, "\n".join(payload))

    return {"summary": summary}


async def fetch_video_for_lang(client, lang, query: str) -> dict[str, Any]:
    try:
        video = await search_video(client, query, lang)
        if not video:
            return {
                "key": lang.key,
                "label": lang.label,
                "emoji": lang.emoji,
                "error": "未找到视频或未配置 YouTube API Key",
            }

        comments = await fetch_comments(client, video["videoId"], lang)
        translated = await _translate_comments(client, comments, lang)

        return {
            "key": lang.key,
            "label": lang.label,
            "emoji": lang.emoji,
            "video": video,
            "comments": translated,
        }
    except Exception as exc:  # pragma: no cover - keep resilient
        return {
            "key": lang.key,
            "label": lang.label,
            "emoji": lang.emoji,
            "error": str(exc),
        }


async def _translate_comments(client, comments: list[dict], lang) -> list[dict]:
    if not comments:
        return []

    tasks = [
        translate_text(client, comment.get("original", ""), lang.mymemory_lang)
        for comment in comments
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    translated = []
    for comment, result in zip(comments, results):
        zh = comment.get("original", "")
        if isinstance(result, Exception):
            zh = comment.get("original", "")
        else:
            zh = result
        translated.append({"original": comment.get("original", ""), "translated": zh})

    return translated


async def fetch_news_for_lang(client, lang, query: str) -> dict[str, Any]:
    try:
        results = await search_news(client, query, lang)
        if not results:
            return {
                "key": lang.key,
                "label": lang.label,
                "emoji": lang.emoji,
                "error": "未找到新闻结果",
            }

        chosen = None
        article = None
        for item in results:
            article = await extract_article(client, item["link"])
            if article:
                chosen = item
                break

        if not article:
            fallback_text = ""
            if chosen and chosen.get("title"):
                fallback_text = chosen.get("title", "")
            if not fallback_text:
                return {
                    "key": lang.key,
                    "label": lang.label,
                    "emoji": lang.emoji,
                    "error": "未找到可免费访问的新闻页面",
                }
            article = {"title": chosen.get("title", ""), "text": fallback_text, "source": chosen.get("source", "")}

        try:
            summary = await summarize_article(
                client,
                query,
                lang.label,
                article["text"],
                output_language=lang.label,
            )
        except Exception:
            summary = clip_text(article["text"], 600)

        summary_zh = await translate_text(client, summary, lang.mymemory_lang)

        return {
            "key": lang.key,
            "label": lang.label,
            "emoji": lang.emoji,
            "article": {
                "title": chosen.get("title") if chosen else article.get("title"),
                "source": chosen.get("source") if chosen else article.get("source"),
                "url": chosen.get("link") if chosen else "",
            },
            "summary": summary,
            "summaryZh": summary_zh,
        }
    except Exception as exc:  # pragma: no cover - keep resilient
        return {
            "key": lang.key,
            "label": lang.label,
            "emoji": lang.emoji,
            "error": str(exc),
        }
