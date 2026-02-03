import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


@dataclass
class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    google_cse_api_key: str = os.getenv("GOOGLE_CSE_API_KEY", "")
    google_cse_id: str = os.getenv("GOOGLE_CSE_ID", "")

    translate_provider: str = os.getenv("TRANSLATE_PROVIDER", "mymemory")
    mymemory_email: str = os.getenv("MYMEMORY_EMAIL", "")

    invidious_base_url: str = os.getenv("INVIDIOUS_BASE_URL", "https://yewtu.be")
    invidious_instances: list[str] = field(
        default_factory=lambda: [
            url.strip()
            for url in os.getenv(
                "INVIDIOUS_INSTANCES",
                "https://yewtu.be,https://vid.puffyan.us,https://inv.nadeko.net,https://invidious.fdn.fr",
            ).split(",")
            if url.strip()
        ]
    )

    gdelt_timespan: str = os.getenv("GDELT_TIMESPAN", "7d")

    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "18"))
    max_concurrency: int = int(os.getenv("MAX_CONCURRENCY", "6"))


settings = Settings()
