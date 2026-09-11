import asyncio
import aiohttp
import feedparser
import re
import logging
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.models.schemas import NewsRecord, NewsContent, Source
from src.storage.db import save_news, is_seen

load_dotenv()
logger = logging.getLogger(__name__)

NEWS_SOURCES = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "Wired AI",        "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
    {"name": "The Verge AI",    "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
]


async def fetch_full_text(session, url):
    """Fetch full article text from article URL."""
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=15),
            headers={"User-Agent": "Mozilla/5.0"}
        ) as r:
            if r.status != 200:
                return None
            html = await r.text()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["nav", "footer", "header", "aside", "script", "style"]):
            tag.decompose()

        container = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"})
        text = container.get_text(" ", strip=True) if container else soup.get_text(" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text[:5000]
    except Exception:
        return None


def parse_feed_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def is_within_24h(dt: datetime | None) -> bool:
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    return 0 <= (now - dt).total_seconds() < 86400


async def fetch_feed(session, source):
    results = []
    try:
        async with session.get(
            source["url"],
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Mozilla/5.0"}
        ) as r:
            content = await r.text()

        feed = feedparser.parse(content)
        print(f"  {source['name']}: {len(feed.entries)} entries found")

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url or is_seen(url):
                continue

            published_at = parse_feed_date(entry)
            if not is_within_24h(published_at):
                continue

            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()[:500]
            author = entry.get("author", None)

            full_text = await fetch_full_text(session, url)

            record = NewsRecord(
                source=Source(name=source["name"], url=source["url"]),
                content=NewsContent(
                    title=title,
                    summary=summary,
                    full_text=full_text,
                    author=author,
                    published_at=published_at,
                    article_url=url,
                ),
                within_24h=True
            )
            save_news(record)
            results.append(record)

    except Exception as e:
        print(f"  ERROR on {source['name']}: {e}")

    return results


async def scrape_news():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, source) for source in NEWS_SOURCES]
        all_results = await asyncio.gather(*tasks)

    total = sum(len(r) for r in all_results)
    print(f"\nNews done. Total articles within 24h: {total}")
    return total


if __name__ == "__main__":
    asyncio.run(scrape_news())