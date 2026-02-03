import re
from urllib.parse import urlparse


PAYWALL_KEYWORDS = [
    "subscribe",
    "subscription",
    "sign in",
    "log in",
    "register to continue",
    "paywall",
    "metered",
    "join to read",
    "already a subscriber",
    "create an account",
    "unlock this article",
]


async def extract_article(client, url: str) -> dict | None:
    import trafilatura
    response = await client.get(url)
    if response.status_code >= 400:
        return None

    html = response.text
    text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
    if not text:
        text = _fallback_extract(html)

    if not text:
        text = await _extract_via_jina(client, url)
    if not text:
        return None

    if _looks_like_paywall(html, text):
        return None

    title = _extract_title(html)
    if not title:
        title = _extract_title_from_jina(text)
    source = urlparse(url).netloc
    return {"title": title, "text": text, "source": source}


def _looks_like_paywall(html: str, text: str) -> bool:
    lowered = html.lower()
    if any(keyword in lowered for keyword in PAYWALL_KEYWORDS):
        return True
    return False


def _fallback_extract(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "aside"]):
        tag.decompose()

    article = soup.find("article")
    if article:
        text = article.get_text(" ", strip=True)
        return text

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 40]
    return " ".join(paragraphs)


def _extract_title(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


async def _extract_via_jina(client, url: str) -> str:
    safe = url.replace("https://", "https://r.jina.ai/https://").replace("http://", "https://r.jina.ai/http://")
    response = await client.get(safe)
    if response.status_code >= 400:
        return ""
    lines = [line.strip() for line in response.text.splitlines() if line.strip()]
    filtered = []
    for line in lines:
        lower = line.lower()
        if lower.startswith(("title:", "url source:", "published time:", "published:", "authors:", "author:", "site name:", "language:", "tags:", "description:", "main content:")):
            continue
        filtered.append(line)
    text = " ".join(filtered)
    return text


def _extract_title_from_jina(text: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith("title:"):
            return line.split(":", 1)[-1].strip()
    return ""
