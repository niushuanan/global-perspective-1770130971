import json
from pathlib import Path

from app.core.constants import LANGUAGES


def load_mock_items() -> list[dict]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "mock_comments.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    videos_by_language = raw.get("videosByLanguage", {})

    items: list[dict] = []
    for lang in LANGUAGES:
        videos = videos_by_language.get(lang.key, [])
        all_comments = []
        for video in videos:
            comments = video.get("comments", [])
            if comments:
                all_comments.extend(comments)
        items.append(
            {
                "key": lang.key,
                "label": lang.label,
                "emoji": lang.emoji,
                "videos": videos,
                "comments": all_comments,
                "commentCount": len(all_comments),
                "videoCount": len(videos),
                "mock": True,
            }
        )
    return items
