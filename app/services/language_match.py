import re


KANA = re.compile(r"[\u3040-\u30ff]")
CJK = re.compile(r"[\u4e00-\u9fff]")
HANGUL = re.compile(r"[\uac00-\ud7af]")

SCRIPT_PATTERNS = {
    "zh": CJK,
    "ko": HANGUL,
}

NON_LATIN = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]")
LATIN = re.compile(r"[A-Za-z]")


def is_language_match(lang_key: str, text: str) -> bool:
    if not text:
        return True
    sample = text.strip()
    if lang_key == "ja":
        if KANA.search(sample):
            return True
        if CJK.search(sample) and not HANGUL.search(sample):
            return True
        return False

    pattern = SCRIPT_PATTERNS.get(lang_key)
    if pattern:
        return bool(pattern.search(sample))

    if len(sample) < 6:
        return True

    non_latin_count = len(NON_LATIN.findall(sample))
    latin_count = len(LATIN.findall(sample))
    if non_latin_count >= 3 and latin_count <= 2:
        return False
    return True
