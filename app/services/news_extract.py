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
    "support our journalism",
    "free trial",
]

PAYWALL_DOMAINS = {
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "economist.com",
    "thetimes.co.uk",
    "theathletic.com",
}


async def extract_article(client, url: str) -> dict | None:
    import trafilatura
    if _is_paywall_domain(url):
        return None

    response = await client.get(url)
    html = ""
    if response.status_code < 400:
        html = response.text
    text = ""

    if html:
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if text and len(text) < 180:
            text = ""
        if not text:
            text = _fallback_extract(html)

    if not text:
        text = await _extract_via_jina(client, url)
    if not text and html:
        text = _extract_meta_description(html)
    if not text:
        return None

    if html and _looks_like_paywall(html, text):
        return None

    title = _extract_title(html) if html else ""
    if not title:
        title = _extract_title_from_jina(text)
    source = urlparse(url).netloc
    return {"title": title, "text": text, "source": source}


def _looks_like_paywall(html: str, text: str) -> bool:
    if len(text) > 800:
        return False
    lowered = html.lower()
    hits = sum(1 for keyword in PAYWALL_KEYWORDS if keyword in lowered)
    return hits >= 2


def _is_paywall_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    host = host.replace("www.", "")
    return any(host == domain or host.endswith(f".{domain}") for domain in PAYWALL_DOMAINS)


def is_probably_paywalled_url(url: str) -> bool:
    return _is_paywall_domain(url)


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


def _extract_meta_description(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
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
        if lower.startswith(
            (
                "title:",
                "url source:",
                "published time:",
                "published:",
                "authors:",
                "author:",
                "site name:",
                "language:",
                "tags:",
                "description:",
            )
        ):
            continue
        if lower.startswith("main content:"):
            filtered.append(line.split(":", 1)[-1].strip())
        else:
            filtered.append(line)
    text = " ".join(filtered)
    return text


def _extract_title_from_jina(text: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith("title:"):
            return line.split(":", 1)[-1].strip()
    return ""
