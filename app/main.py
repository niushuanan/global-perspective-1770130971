import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.constants import LANGUAGES
from app.services.comment_filter import filter_comments
from app.services.http_client import get_client
from app.services.summarize import summarize_comments_local, summarize_comments_overview
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
    scope: str | None = None


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


@app.post("/api/summary/comments")
async def summarize_comments(request: SummaryRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    payload = _build_comments_summary_payload(request.items)
    if not payload:
        raise HTTPException(status_code=400, detail="No comments provided")

    scope = request.scope or ("local" if len(request.items) == 1 else "global")

    async with get_client() as client:
        try:
            if scope == "local":
                summary = await summarize_comments_local(client, query, payload)
            else:
                summary = await summarize_comments_overview(client, query, payload)
        except Exception:
            summary = "暂时无法生成 AI 总结，请稍后再试。"

    return {"summary": summary}


async def fetch_video_for_lang(client, lang, query: str) -> dict[str, Any]:
    try:
        localized_query = await translate_text(client, query, "auto", lang.mymemory_lang)
        videos = await search_videos(client, localized_query or query, lang, limit=10)
        if not videos:
            return {
                "key": lang.key,
                "label": lang.label,
                "emoji": lang.emoji,
                "error": "未找到视频或未配置 YouTube API Key",
            }

        per_video = 5
        video_entries = []
        all_comments = []
        for video in videos:
            raw_comments = await fetch_comments(
                client,
                video["videoId"],
                lang,
                max_results=40,
            )
            filtered = filter_comments(raw_comments, lang.key, per_video)
            translated = await _translate_comments(client, filtered, lang)
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
            "commentCount": len(all_comments),
            "videoCount": len(video_entries),
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


def _build_comments_summary_payload(items: list[dict[str, Any]]) -> str:
    payload = []
    for item in items:
        label = item.get("label", "")
        comments = item.get("comments") or []
        if not comments:
            continue
        sample = comments[:12]
        joined = " / ".join(
            [
                clip_text(c.get("translated") or c.get("original", ""), 200)
                for c in sample
                if c.get("translated") or c.get("original")
            ]
        )
        if joined:
            payload.append(f"{label}: {joined}")
    if not payload:
        return ""
    return "\n".join(payload)
