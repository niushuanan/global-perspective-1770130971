from app.core.config import settings


class TranslateError(RuntimeError):
    pass


async def translate_text(client, text: str, source_lang: str, target_lang: str = "zh-CN") -> str:
    if not text:
        return ""
    if source_lang.lower().startswith("zh") and target_lang.lower().startswith("zh"):
        return text

    provider = settings.translate_provider.lower()
    if provider == "mymemory":
        return await _translate_mymemory(client, text, source_lang, target_lang)

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
