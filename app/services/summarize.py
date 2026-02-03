from app.services.deepseek import chat
from app.services.utils import clip_text


async def summarize_article(client, query: str, lang_label: str, text: str, output_language: str) -> str:
    clipped = clip_text(text)
    system = "你是资深新闻编辑，擅长将报道整理为结构化摘要。"
    user = (
        "请将下面的新闻正文总结为中等长度摘要，约保留原文信息量的50%。\n"
        "要求：保留关键事实、时间、影响与不同观点；避免空泛评价。\n"
        f"请用以下语言输出：{output_language}\n"
        f"事件关键词：{query}\n"
        f"语言来源：{lang_label}\n"
        f"正文：{clipped}"
    )
    return await chat(
        client,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=900,
    )


async def summarize_comments_overview(client, query: str, comments_payload: str) -> str:
    system = "你是跨语言舆情分析专家，擅长提炼不同国家/语言群体的态度差异。"
    user = (
        "请基于多语言评论内容生成结构化报告：\n"
        "1) 总体情绪倾向\n"
        "2) 各语言/地区主要观点（每组1-2条）\n"
        "3) 观点差异与可能原因\n"
        "要求：用中文输出，语气中立，结构清晰。\n"
        f"事件关键词：{query}\n"
        f"评论内容：{comments_payload}"
    )
    return await chat(
        client,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=700,
    )


async def summarize_news_overview(client, query: str, summaries_payload: str) -> str:
    system = "你是国际媒体观察员，擅长比较多国媒体报道角度和立场。"
    user = (
        "请基于多国新闻摘要生成综合报告：\n"
        "1) 共同关注点\n"
        "2) 各国媒体报道侧重点差异\n"
        "3) 可能的立场/叙事差别\n"
        "要求：用中文输出，结构化，避免情绪化措辞。\n"
        f"事件关键词：{query}\n"
        f"摘要内容：{summaries_payload}"
    )
    return await chat(
        client,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=700,
    )
