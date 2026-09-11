import asyncio
import aiohttp
import feedparser
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.models.schemas import JobRecord, JobContent, Source
from src.storage.db import save_job, is_seen

load_dotenv()
logger = logging.getLogger(__name__)

JOB_SOURCES = [
    {"name": "RemoteOK AI",      "url": "https://remoteok.com/remote-ai-jobs.rss"},
    {"name": "HackerNews Jobs",  "url": "https://hnrss.org/jobs"},
    {"name": "We Work Remotely", "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss"},
    {"name": "Remotive AI",      "url": "https://remotive.com/remote-jobs/feed/software-dev"},
    {"name": "AI Jobs",          "url": "https://aijobs.net/feed/"},
]


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
        # if no date found, assume it's recent and include it
        return True
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() < 86400


def extract_company(entry) -> str | None:
    for field in ("author", "publisher"):
        val = getattr(entry, field, None)
        if val and isinstance(val, str):
            return val.strip()
    return None


async def fetch_jobs(session, source):
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

            posted_at = parse_feed_date(entry)

            if not is_within_24h(posted_at):
                continue

            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()[:500]
            company = extract_company(entry)

            record = JobRecord(
                source=Source(name=source["name"], url=source["url"]),
                content=JobContent(
                    title=title,
                    company=company,
                    description=summary,
                    posted_at=posted_at,
                    job_url=url,
                ),
                within_24h=True
            )
            save_job(record)
            results.append(record)

    except Exception as e:
        print(f"  ERROR on {source['name']}: {e}")

    return results


async def scrape_jobs():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_jobs(session, source) for source in JOB_SOURCES]
        all_results = await asyncio.gather(*tasks)

    total = sum(len(r) for r in all_results)
    print(f"\nJobs done. Total jobs within 24h: {total}")
    return total


if __name__ == "__main__":
    asyncio.run(scrape_jobs())