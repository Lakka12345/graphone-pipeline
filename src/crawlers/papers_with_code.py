import asyncio
import aiohttp
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
    if not github_url:
        return None
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


async def scrape_huggingface_papers(target=500):
    """Fetch papers from HuggingFace Papers API (replaces Papers with Code)."""
    saved = 0
    page = 0
    page_size = 100

    async with aiohttp.ClientSession() as session:
        while saved < target:
            url = f"https://huggingface.co/api/papers?limit={page_size}&offset={page * page_size}"
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as r:
                    if r.status != 200:
                        print(f"  Page {page} returned {r.status}, stopping")
                        break
                    papers = await r.json()
            except Exception as e:
                print(f"  Error on page {page}: {e}")
                break

            if not papers:
                print(f"  No more papers at page {page}")
                break

            for paper in papers:
                if saved >= target:
                    break

                arxiv_id = paper.get("id", "")
                paper_url = f"https://arxiv.org/abs/{arxiv_id}"

                if not arxiv_id or is_seen(paper_url):
                    continue

                authors = [
                    a.get("name", "") for a in paper.get("authors", [])
                    if isinstance(a, dict)
                ]

                published = None
                pub_str = paper.get("publishedAt", None)
                if pub_str:
                    try:
                        published = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                # Look for GitHub link in abstract
                abstract = paper.get("summary", "") or ""
                github_url = None
                gh_match = re.search(r"https?://github\.com/[^\s\)\]\"]+", abstract)
                if gh_match:
                    github_url = gh_match.group(0)

                stars = await get_github_stars(session, github_url)

                record = PaperRecord(
                    source=Source(name="HuggingFace Papers", url=paper_url),
                    content=PaperContent(
                        title=paper.get("title", "").strip(),
                        authors=authors,
                        abstract=abstract[:500] or None,
                        paper_url=paper_url,
                        github_url=github_url,
                        github_stars=stars,
                        published_date=published,
                    )
                )
                save_paper(record)
                saved += 1

            print(f"  Page {page}: {len(papers)} papers | Total saved: {saved}")
            page += 1
            await asyncio.sleep(0.5)

    print(f"\nHuggingFace Papers done. Total saved: {saved}")
    return saved


if __name__ == "__main__":
    asyncio.run(scrape_huggingface_papers(500))