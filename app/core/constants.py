from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageConfig:
    key: str
    label: str
    emoji: str
    youtube_lang: str
    youtube_region: str
    google_lr: str
    google_hl: str
    google_gl: str
    google_ceid: str
    mymemory_lang: str


LANGUAGES = [
    LanguageConfig(
        key="zh",
        label="中文",
        emoji="🇨🇳",
        youtube_lang="zh-Hans",
        youtube_region="CN",
        google_lr="lang_zh-CN",
        google_hl="zh-CN",
        google_gl="CN",
        google_ceid="CN:zh-Hans",
        mymemory_lang="zh-CN",
    ),
    LanguageConfig(
        key="en",
        label="English",
        emoji="🇺🇸",
        youtube_lang="en",
        youtube_region="US",
        google_lr="lang_en",
        google_hl="en-US",
        google_gl="US",
        google_ceid="US:en",
        mymemory_lang="en",
    ),
    LanguageConfig(
        key="ja",
        label="日本語",
        emoji="🇯🇵",
        youtube_lang="ja",
        youtube_region="JP",
        google_lr="lang_ja",
        google_hl="ja",
        google_gl="JP",
        google_ceid="JP:ja",
        mymemory_lang="ja",
    ),
    LanguageConfig(
        key="de",
        label="Deutsch",
        emoji="🇩🇪",
        youtube_lang="de",
        youtube_region="DE",
        google_lr="lang_de",
        google_hl="de",
        google_gl="DE",
        google_ceid="DE:de",
        mymemory_lang="de",
    ),
    LanguageConfig(
        key="fr",
        label="Français",
        emoji="🇫🇷",
        youtube_lang="fr",
        youtube_region="FR",
        google_lr="lang_fr",
        google_hl="fr",
        google_gl="FR",
        google_ceid="FR:fr",
        mymemory_lang="fr",
    ),
    LanguageConfig(
        key="es",
        label="Español",
        emoji="🇪🇸",
        youtube_lang="es",
        youtube_region="ES",
        google_lr="lang_es",
        google_hl="es",
        google_gl="ES",
        google_ceid="ES:es",
        mymemory_lang="es",
    ),
    LanguageConfig(
        key="pt",
        label="Português",
        emoji="🇧🇷",
        youtube_lang="pt",
        youtube_region="BR",
        google_lr="lang_pt",
        google_hl="pt-BR",
        google_gl="BR",
        google_ceid="BR:pt-419",
        mymemory_lang="pt",
    ),
]
