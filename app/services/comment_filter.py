import re

from app.services.language_match import is_language_match


LINK_PATTERN = re.compile(r"(https?://|www\.|\b\w+\.\w{2,})", re.IGNORECASE)

GLOBAL_KEYWORDS = [
    "promo",
    "promotion",
    "discount",
    "coupon",
    "free",
    "giveaway",
    "deal",
    "sale",
    "subscribe",
    "follow",
    "link in bio",
    "contact me",
    "dm me",
    "whatsapp",
    "telegram",
    "wechat",
    "line",
]

LANGUAGE_KEYWORDS = {
    "zh": [
        "代购",
        "返利",
        "优惠",
        "折扣",
        "领券",
        "福利",
        "加群",
        "加我",
        "微信",
        "VX",
        "私信",
        "联系方式",
        "关注我",
        "点赞收藏",
        "点我主页",
        "点链接",
    ],
    "en": [
        "promo code",
        "coupon code",
        "follow me",
        "subscribe",
        "check my channel",
        "my link",
        "link",
    ],
    "ja": [
        "割引",
        "クーポン",
        "無料",
        "フォローして",
        "チャンネル登録",
        "登録して",
        "リンク",
        "公式ライン",
        "LINE",
    ],
    "de": [
        "rabatt",
        "gutschein",
        "gratis",
        "folge",
        "abonniere",
        "abonnieren",
        "link",
        "angebot",
    ],
    "fr": [
        "promo",
        "réduction",
        "coupon",
        "gratuit",
        "abonnez",
        "abonne-toi",
        "lien",
        "offre",
    ],
    "es": [
        "oferta",
        "descuento",
        "cupón",
        "gratis",
        "sígueme",
        "suscríbete",
        "enlace",
        "promo",
    ],
    "pt": [
        "oferta",
        "desconto",
        "cupom",
        "grátis",
        "siga",
        "inscreva-se",
        "link",
        "promoção",
    ],
    "ko": [
        "할인",
        "쿠폰",
        "무료",
        "구독",
        "팔로우",
        "링크",
        "카톡",
        "카카오",
        "문의",
        "프로모션",
    ],
}


def filter_comments(
    comments: list[dict],
    lang_key: str,
    limit: int,
    use_lang_match: bool = False,
) -> list[dict]:
    filtered = []
    for comment in comments:
        text = (comment.get("original") or "").strip()
        if not text:
            continue
        if _contains_link(text):
            continue
        if _is_low_info(text):
            continue
        if _contains_blacklist(text, lang_key):
            continue
        if use_lang_match and not is_language_match(lang_key, text):
            continue
        filtered.append(comment)

    filtered.sort(key=lambda x: x.get("likeCount", 0), reverse=True)
    return filtered[:limit]


def _contains_link(text: str) -> bool:
    return bool(LINK_PATTERN.search(text))


def _is_low_info(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 5:
        return True
    info_count = sum(1 for ch in stripped if _is_info_char(ch))
    return info_count < 5


def _is_info_char(ch: str) -> bool:
    if ch.isalnum():
        return True
    return _is_cjk(ch)


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff" or "\uac00" <= ch <= "\ud7af"


def _contains_blacklist(text: str, lang_key: str) -> bool:
    lowered = text.lower()
    for keyword in GLOBAL_KEYWORDS:
        if keyword in lowered:
            return True
    for keyword in LANGUAGE_KEYWORDS.get(lang_key, []):
        if keyword.isascii():
            if keyword in lowered:
                return True
        else:
            if keyword in text:
                return True
    return False
