import asyncio

from app.core.config import settings


class DeepSeekError(RuntimeError):
    pass


def _build_url(path: str) -> str:
    base = settings.deepseek_base_url.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


async def chat(client, messages, temperature=0.2, max_tokens=800):
    if not settings.deepseek_api_key:
        raise DeepSeekError("Missing DEEPSEEK_API_KEY")

    payload = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_error = None
    for attempt in range(3):
        response = await client.post(
            _build_url("chat/completions"),
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if response.status_code in {401, 429, 500, 502, 503, 504}:
            last_error = f"DeepSeek transient error {response.status_code}"
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
        response.raise_for_status()
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError("Unexpected DeepSeek response format") from exc

    raise DeepSeekError(last_error or "DeepSeek request failed")
