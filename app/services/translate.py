from app.core.config import settings
from app.services.deepseek import chat, DeepSeekError


class TranslateError(RuntimeError):
    pass


async def translate_text(client, text: str, source_lang: str, target_lang: str = "zh-CN") -> str:
    if not text:
        return ""
    if source_lang.lower().startswith("zh") and target_lang.lower().startswith("zh"):
        return text

    provider = settings.translate_provider.lower()
    if provider == "mymemory":
        try:
            return await _translate_mymemory(client, text, source_lang, target_lang)
        except Exception:
            if settings.deepseek_api_key:
                return await _translate_deepseek(client, text, source_lang, target_lang)
            raise
    if provider == "deepseek":
        return await _translate_deepseek(client, text, source_lang, target_lang)

    raise TranslateError(f"Unsupported translation provider: {settings.translate_provider}")


async def _translate_mymemory(client, text: str, source_lang: str, target_lang: str) -> str:
    params = {
        "q": text,
        "langpair": f"{source_lang}|{target_lang}",
    }
    if settings.mymemory_email:
        params["de"] = settings.mymemory_email

    response = await client.get("https://api.mymemory.translated.net/get", params=params)
    response.raise_for_status()
    data = response.json()
    translated = data.get("responseData", {}).get("translatedText")
    if not translated:
        return text
    return translated


async def _translate_deepseek(client, text: str, source_lang: str, target_lang: str) -> str:
    system = "你是专业翻译引擎，只输出翻译结果，不要添加解释。"
    user = (
        f"请将以下文本从 {source_lang} 翻译为 {target_lang}，保持原意与语气：\n{text}"
    )
    try:
        return await chat(
            client,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=600,
        )
    except DeepSeekError:
        return text
