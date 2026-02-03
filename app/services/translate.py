import json
import re

from app.core.config import settings
from app.services.deepseek import chat, DeepSeekError


class TranslateError(RuntimeError):
    pass


def _looks_cjk(text: str) -> bool:
    for char in text:
        if "\u4e00" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff":
            return True
    return False


async def translate_text(client, text: str, source_lang: str, target_lang: str = "zh-CN") -> str:
    if not text:
        return ""
    if source_lang.lower().startswith("zh") and target_lang.lower().startswith("zh"):
        return text
    if source_lang == "auto" and target_lang.lower().startswith("zh") and _looks_cjk(text):
        return text

    provider = settings.translate_provider.lower()
    if provider == "mymemory":
        if source_lang == "auto":
            if settings.deepseek_api_key:
                return await _translate_deepseek(client, text, source_lang, target_lang)
            return text
        try:
            return await _translate_mymemory(client, text, source_lang, target_lang)
        except Exception:
            if settings.deepseek_api_key:
                return await _translate_deepseek(client, text, source_lang, target_lang)
            raise
    if provider == "deepseek":
        return await _translate_deepseek(client, text, source_lang, target_lang)

    raise TranslateError(f"Unsupported translation provider: {settings.translate_provider}")


async def translate_texts(
    client,
    texts: list[str],
    source_lang: str,
    target_lang: str = "zh-CN",
) -> list[str]:
    if not texts:
        return []

    provider = settings.translate_provider.lower()
    if provider == "deepseek":
        try:
            return await _translate_deepseek_batch(client, texts, source_lang, target_lang)
        except DeepSeekError:
            return await _translate_fallback_batch(client, texts, source_lang, target_lang)

    if provider == "mymemory":
        return await _translate_fallback_batch(client, texts, source_lang, target_lang)

    raise TranslateError(f"Unsupported translation provider: {settings.translate_provider}")


async def _translate_fallback_batch(
    client,
    texts: list[str],
    source_lang: str,
    target_lang: str,
) -> list[str]:
    results = []
    for text in texts:
        try:
            results.append(await translate_text(client, text, source_lang, target_lang))
        except Exception:
            results.append(text)
    return results


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
        "请进行快速、地道的翻译，保持原意与语气，不要增加或删减信息。\n"
        f"源语言：{source_lang}\n"
        f"目标语言：{target_lang}\n"
        f"文本：{text}"
    )
    try:
        return await chat(
            client,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=900,
        )
    except DeepSeekError:
        return text


async def _translate_deepseek_batch(
    client,
    texts: list[str],
    source_lang: str,
    target_lang: str,
) -> list[str]:
    system = "你是专业翻译引擎，只输出翻译结果，不要添加解释。"
    payload = json.dumps(texts, ensure_ascii=False)
    user = (
        "请进行快速、地道的翻译，保持原意与语气。\n"
        "要求：仅输出 JSON 数组，顺序与输入一致，不要添加额外文本或代码块。\n"
        f"源语言：{source_lang}\n"
        f"目标语言：{target_lang}\n"
        f"文本列表：{payload}"
    )
    response = await chat(
        client,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    translations = _extract_json_array(response)
    if len(translations) != len(texts):
        raise DeepSeekError("Batch translation length mismatch")
    return [str(item) for item in translations]


def _extract_json_array(text: str) -> list:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise DeepSeekError("No JSON array found in translation response")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise DeepSeekError("Failed to parse translation JSON") from exc
