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
        return None

    if _looks_like_paywall(html, text):
        return None

    title = _extract_title(html)
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
