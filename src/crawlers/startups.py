import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

from src.models.schemas import StartupRecord, StartupContent, Source
from src.storage.db import save_startup, is_seen

load_dotenv()
logger = logging.getLogger(__name__)

YC_API = "https://api.ycombinator.com/v0.1/companies?page={page}"


async def scrape_yc_startups(target=1000):
    """Scrape YC company directory via their public API."""
    saved = 0
    page = 1

    async with aiohttp.ClientSession() as session:
        while saved < target:
            url = YC_API.format(page=page)
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as r:
                    if r.status != 200:
                        print(f"  Page {page} returned status {r.status}, stopping")
                        break
                    data = await r.json()
            except Exception as e:
                print(f"  Error on page {page}: {e}")
                break

            companies = data.get("companies", [])
            if not companies:
                print(f"  No more companies at page {page}")
                break

            for company in companies:
                if saved >= target:
                    break

                website = company.get("website", "") or ""
                name = company.get("name", "").strip()
                source_url = f"https://www.ycombinator.com/companies/{company.get('slug', '')}"

                if not name or is_seen(source_url):
                    continue

                record = StartupRecord(
                    source=Source(name="Y Combinator", url=source_url),
                    content=StartupContent(
                        entity_name=name,
                        description=company.get("one_liner", None),
                        founded_year=company.get("year_founded", None),
                        employee_count=None,  # not provided by YC
                        location=company.get("location", None),
                        website=website or None,
                    )
                )
                save_startup(record)
                saved += 1

            print(f"  Page {page}: {len(companies)} companies | Total saved: {saved}")
            page += 1
            await asyncio.sleep(0.5)  # be polite

    print(f"\nStartups done. Total saved: {saved}")
    return saved


if __name__ == "__main__":
    asyncio.run(scrape_yc_startups(1000))