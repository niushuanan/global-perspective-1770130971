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
from app.services.news_extract import extract_article, is_probably_paywalled_url
from app.services.google_search import search_news
from app.services.summarize import (
    summarize_article,
    summarize_comments_overview,
    summarize_news_overview,
)
from app.services.translate import translate_text, translate_texts
from app.services.utils import clip_text
from app.services.youtube import fetch_comments, search_videos

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

    summary = _build_comments_summary_payload(results, query)
    if summary:
        async with get_client() as client:
            try:
                summary = await summarize_comments_overview(client, query, summary)
            except Exception:
                summary = "暂时无法生成 AI 总结，请稍后再试。"

    return {"query": query, "items": results, "summary": summary}


@app.post("/api/news")
async def analyze_news(request: QueryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    async with get_client() as client:
        tasks = [fetch_news_for_lang(client, lang, query) for lang in LANGUAGES]
        results = await asyncio.gather(*tasks)

    summary_payload = _build_news_summary_payload(results)
    if summary_payload:
        async with get_client() as client:
            try:
                summary_text = await summarize_news_overview(client, query, summary_payload)
            except Exception:
                summary_text = "暂时无法生成 AI 总结，请稍后再试。"
    else:
        summary_text = ""

    return {"query": query, "items": results, "summary": summary_text}


@app.post("/api/summary/comments")
async def summarize_comments(request: SummaryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    payload = _build_comments_summary_payload(request.items, query)

    if not payload:
        raise HTTPException(status_code=400, detail="No comments provided")

    async with get_client() as client:
        try:
            summary = await summarize_comments_overview(client, query, payload)
        except Exception:
            summary = "暂时无法生成 AI 总结，请稍后再试。"

    return {"summary": summary}


@app.post("/api/summary/news")
async def summarize_news(request: SummaryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    payload = _build_news_summary_payload(request.items)

    if not payload:
        raise HTTPException(status_code=400, detail="No summaries provided")

    async with get_client() as client:
        try:
            summary = await summarize_news_overview(client, query, payload)
        except Exception:
            summary = "暂时无法生成 AI 总结，请稍后再试。"

    return {"summary": summary}


async def fetch_video_for_lang(client, lang, query: str) -> dict[str, Any]:
    try:
        localized_query = await translate_text(client, query, "auto", lang.mymemory_lang)
        videos = await search_videos(client, localized_query or query, lang, limit=2)
        if not videos:
            return {
                "key": lang.key,
                "label": lang.label,
                "emoji": lang.emoji,
                "error": "未找到视频或未配置 YouTube API Key",
            }

        per_video = 10 if len(videos) >= 2 else 20
        video_entries = []
        all_comments = []
        for video in videos:
            comments = await fetch_comments(client, video["videoId"], lang, limit=per_video)
            translated = await _translate_comments(client, comments, lang)
            video_entries.append(
                {
                    **video,
                    "comments": translated,
                }
            )
            all_comments.extend(translated)
        return {
            "key": lang.key,
            "label": lang.label,
            "emoji": lang.emoji,
            "videos": video_entries,
            "comments": all_comments,
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

    originals = [comment.get("original", "") for comment in comments]
    results = await translate_texts(client, originals, lang.mymemory_lang, "zh-CN")

    translated = []
    for comment, zh in zip(comments, results):
        translated.append(
            {
                "original": comment.get("original", ""),
                "translated": zh or comment.get("original", ""),
                "likeCount": comment.get("likeCount", 0),
            }
        )
    return translated


async def fetch_news_for_lang(client, lang, query: str) -> dict[str, Any]:
    try:
        localized_query = await translate_text(client, query, "auto", lang.mymemory_lang)
        results = await search_news(client, localized_query or query, lang)
        if not results:
            return {
                "key": lang.key,
                "label": lang.label,
                "emoji": lang.emoji,
                "error": "未找到新闻结果",
            }

        chosen = None
        article = None
        fallback_item = None
        for item in results:
            if is_probably_paywalled_url(item.get("link", "")):
                continue
            article = await extract_article(client, item["link"])
            if article:
                chosen = item
                break
            if not fallback_item and item.get("summary"):
                fallback_item = item

        if not article:
            chosen = fallback_item or (results[0] if results else None)
            if not chosen:
                return {
                    "key": lang.key,
                    "label": lang.label,
                    "emoji": lang.emoji,
                    "error": "未找到可免费访问的新闻页面",
                }
            fallback_text = _clean_fallback_text(chosen.get("summary", "") or chosen.get("title", ""))
            if not fallback_text:
                return {
                    "key": lang.key,
                    "label": lang.label,
                    "emoji": lang.emoji,
                    "error": "未找到可免费访问的新闻页面",
                }
            article = {
                "title": chosen.get("title", ""),
                "text": fallback_text,
                "source": chosen.get("source", ""),
            }

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


def _clean_fallback_text(text: str) -> str:
    if not text:
        return ""
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _build_comments_summary_payload(items: list[dict[str, Any]], query: str) -> str:
    payload = []
    for item in items:
        label = item.get("label", "")
        comments = item.get("comments") or []
        if not comments and item.get("videos"):
            comments = [
                comment
                for video in item.get("videos", [])
                for comment in video.get("comments", [])
            ]
        if not comments:
            continue
        sample = comments[:8]
        joined = " / ".join([clip_text(c.get("original", ""), 200) for c in sample if c.get("original")])
        if joined:
            payload.append(f"{label}: {joined}")
    if not payload:
        return ""
    return "\n".join(payload)


def _build_news_summary_payload(items: list[dict[str, Any]]) -> str:
    payload = []
    for item in items:
        label = item.get("label", "")
        summary = item.get("summary", "")
        if summary:
            payload.append(f"{label}: {clip_text(summary, 600)}")
    if not payload:
        return ""
    return "\n".join(payload)
