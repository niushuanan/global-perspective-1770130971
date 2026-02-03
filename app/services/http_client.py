from contextlib import asynccontextmanager

import httpx

from app.core.config import settings


@asynccontextmanager
async def get_client():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=settings.http_timeout, headers=headers, follow_redirects=True) as client:
        yield client
