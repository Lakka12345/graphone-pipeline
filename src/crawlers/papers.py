import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import re
import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.models.schemas import PaperRecord, PaperContent, Source
from src.storage.db import save_paper, is_seen

load_dotenv()
logger = logging.getLogger(__name__)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


async def get_github_stars(session, github_url):
    """Hit GitHub API for live star count."""
    m = re.search(r"github\.com/([^/]+/[^/\s#?]+)", github_url)
    if not m:
        return None
    repo = m.group(1).rstrip("/")
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        async with session.get(
            f"https://api.github.com/repos/{repo}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("stargazers_count")
    except Exception:
        pass
    return None


async def scrape_arxiv(max_results=1000):
    """Fetch AI papers from arXiv. Returns count of saved papers."""
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query=cat:cs.AI&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    async with aiohttp.ClientSession() as session:
        print("Fetching arXiv papers...")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
            xml_text = await r.text()

        root = ET.fromstring(xml_text)
        entries = root.findall("atom:entry", ns)
        print(f"Got {len(entries)} entries from arXiv")

        saved = 0
        for entry in entries:
            paper_url = entry.find("atom:id", ns).text.strip()

            if is_seen(paper_url):
                continue

            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")

            authors = [
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
            ]

            published_str = entry.find("atom:published", ns).text
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

            abstract = entry.find("atom:summary", ns).text or ""

            # Look for GitHub link in abstract
            github_url = None
            gh_match = re.search(r"https?://github\.com/[^\s\)\]\"]+", abstract)
            if gh_match:
                github_url = gh_match.group(0)

            # Get live GitHub stars
            stars = None
            if github_url:
                stars = await get_github_stars(session, github_url)

            record = PaperRecord(
                source=Source(name="arXiv", url=paper_url),
                content=PaperContent(
                    title=title,
                    authors=authors,
                    abstract=abstract[:500],
                    paper_url=paper_url,
                    github_url=github_url,
                    github_stars=stars,
                    published_date=published,
                )
            )
            save_paper(record)
            saved += 1

            if saved % 100 == 0:
                print(f"  Saved {saved} papers...")

        print(f"Done. Total saved: {saved} papers")
        return saved


if __name__ == "__main__":
    asyncio.run(scrape_arxiv(1000))