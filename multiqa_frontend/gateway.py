import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
LOCAL_SECRET_FILE = BASE_DIR / "secrets.local.json"

MAX_ATTEMPTS = 3
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}

try:
    LOCAL_SECRETS = json.loads(LOCAL_SECRET_FILE.read_text(encoding="utf-8")) if LOCAL_SECRET_FILE.exists() else {}
except Exception:
    LOCAL_SECRETS = {}

PROVIDERS = {
    "zhipu": {
        "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "key_env": "ZHIPU_API_KEY",
        "default_key": "",
        "default_model": "glm-5",
        "default_system": "你是一个有用的AI助手。",
    },
    "moonshot": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "key_env": "MOONSHOT_API_KEY",
        "default_key": "",
        "default_model": "kimi-2.5-thinking",
        "default_system": "你是一个有用的AI助手。",
    },
    "minimax": {
        "url": "https://api.minimaxi.com/anthropic/v1/messages",
        "key_env": "MINIMAX_API_KEY",
        "default_key": "",
        "default_model": "MiniMax-M2.1",
        "default_system": "你是一个有用的AI助手。",
    },
}

app = FastAPI(title="MultiQA Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_provider(provider: str) -> dict[str, str]:
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise HTTPException(status_code=404, detail="未支持的提供方")
    return cfg


def get_api_key(cfg: dict[str, str]) -> str:
    key_name = cfg["key_env"]
    return (
        os.getenv(key_name, "")
        or str(LOCAL_SECRETS.get(key_name, ""))
        or cfg["default_key"]
    ).strip()


def build_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload or {})
    normalized["stream"] = True

    cfg = get_provider(provider)
    normalized.setdefault("model", cfg["default_model"])
    normalized.setdefault("temperature", 0.6)

    messages = normalized.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")

    if provider == "zhipu":
        first = messages[0] if messages else {}
        if first.get("role") != "system":
            messages = [{"role": "system", "content": cfg["default_system"]}] + messages
            normalized["messages"] = messages
    elif provider == "minimax":
        normalized["model"] = "MiniMax-M2.1"
        normalized["max_tokens"] = int(normalized.get("max_tokens", 2048))
        normalized["system"] = normalized.get("system") or cfg["default_system"]
        new_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            new_messages.append({"role": role, "content": content})
        normalized["messages"] = new_messages

    return normalized


def normalize_error_message(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return "请求失败"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or text)
        msg = payload.get("message")
        if msg:
            return str(msg)
    return text


def extract_delta_text(data: dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return ""

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0] or {}
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )

        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )

    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text

    delta = data.get("delta")
    if isinstance(delta, dict):
        text = delta.get("text")
        if isinstance(text, str):
            return text

    content_block = data.get("content_block")
    if isinstance(content_block, dict) and content_block.get("type") == "text":
        text = content_block.get("text")
        if isinstance(text, str):
            return text

    return ""


async def open_upstream_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> httpx.Response:
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            request = client.build_request("POST", url, headers=headers, json=payload)
            response = await client.send(request, stream=True)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            last_error = exc
            if attempt >= MAX_ATTEMPTS:
                break
            await asyncio.sleep(0.7 * attempt)
            continue

        if response.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
            await response.aread()
            await response.aclose()
            delay = (1.4 if response.status_code == 429 else 0.7) * attempt
            await asyncio.sleep(delay)
            continue

        return response

    raise RuntimeError(str(last_error or "上游请求失败"))


def to_sse_delta(delta: str) -> str:
    payload = {"choices": [{"delta": {"content": delta}}]}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/")
async def index() -> FileResponse:
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="index.html 不存在")
    return FileResponse(INDEX_FILE)


@app.get("/local_keys.js")
async def local_keys_js():
    file = BASE_DIR / "local_keys.js"
    if file.exists():
        return FileResponse(file, media_type="application/javascript")
    return Response("window.__LOCAL_KEYS__ = {};\n", media_type="application/javascript")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/{provider}/chat/completions")
async def proxy_chat(provider: str, request: Request):
    provider = provider.lower()
    cfg = get_provider(provider)

    try:
        incoming = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {exc}") from exc

    if not isinstance(incoming, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")

    payload = build_payload(provider, incoming)
    api_key = get_api_key(cfg)
    if not api_key:
        raise HTTPException(status_code=500, detail=f"缺少 {cfg['key_env']} 配置")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if provider == "minimax":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"

    client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=30.0))
    try:
        upstream = await open_upstream_with_retry(client, cfg["url"], headers, payload)
    except Exception as exc:
        await client.aclose()
        message = normalize_error_message(str(exc))
        return JSONResponse(status_code=504, content={"error": {"message": message}})

    if upstream.status_code == 404 and provider == "moonshot":
        raw_404 = await upstream.aread()
        message_404 = normalize_error_message(raw_404.decode("utf-8", "ignore"))
        fallback_model = os.getenv("MOONSHOT_FALLBACK_MODEL", "kimi-k2-0711-preview").strip()
        if (
            fallback_model
            and payload.get("model") != fallback_model
            and ("Not found the model" in message_404 or "Permission denied" in message_404)
        ):
            await upstream.aclose()
            retry_payload = dict(payload)
            retry_payload["model"] = fallback_model
            try:
                upstream = await open_upstream_with_retry(client, cfg["url"], headers, retry_payload)
            except Exception:
                await client.aclose()
                return JSONResponse(status_code=404, content={"error": {"message": message_404}})
        else:
            await upstream.aclose()
            await client.aclose()
            return JSONResponse(status_code=404, content={"error": {"message": message_404}})

    if upstream.status_code >= 400:
        raw = await upstream.aread()
        message = normalize_error_message(raw.decode("utf-8", "ignore"))
        await upstream.aclose()
        await client.aclose()
        return JSONResponse(status_code=upstream.status_code, content={"error": {"message": message}})

    async def event_stream():
        aggregated = ""
        saw_sse = False
        non_sse_buffer: list[str] = []
        try:
            async for line in upstream.aiter_lines():
                if not line:
                    continue
                trimmed = line.strip()
                if not trimmed.startswith("data:"):
                    non_sse_buffer.append(trimmed)
                    continue

                saw_sse = True
                data = trimmed[5:].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break

                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue

                delta = extract_delta_text(parsed)
                if not delta:
                    continue

                aggregated += delta
                yield to_sse_delta(delta)

            if (not saw_sse) and non_sse_buffer:
                raw_json = "".join(non_sse_buffer)
                try:
                    parsed = json.loads(raw_json)
                except json.JSONDecodeError:
                    parsed = {}
                delta = extract_delta_text(parsed)
                if delta:
                    yield to_sse_delta(delta)

            if aggregated:
                yield "data: [DONE]\n\n"
            else:
                # 保底返回空完成信号，避免前端一直等待。
                yield "data: [DONE]\n\n"
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("gateway:app", host="127.0.0.1", port=8787, reload=True)
