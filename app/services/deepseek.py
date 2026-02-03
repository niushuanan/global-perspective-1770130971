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

    response = await client.post(
        _build_url("chat/completions"),
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )

    response.raise_for_status()
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekError("Unexpected DeepSeek response format") from exc
