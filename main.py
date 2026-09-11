"""
Main pipeline runner — runs all scrapers in sequence.
"""
import asyncio
from src.storage.db import init_db, counts
from src.crawlers.papers import scrape_arxiv
from src.crawlers.news import scrape_news
from src.crawlers.jobs import scrape_jobs
from src.crawlers.startups import scrape_yc_startups
from src.crawlers.products import scrape_products
from src.entity_resolution.resolver import resolve_all_startups
from src.storage.sheets import export_all


async def main():
    print("=== GraphOne Pipeline ===\n")

    print("[1/7] Initializing database...")
    init_db()

    print("[2/7] Scraping research papers...")
    await scrape_arxiv(1000)

    print("[3/7] Scraping news...")
    await scrape_news()

    print("[4/7] Scraping jobs...")
    await scrape_jobs()

    print("[5/7] Scraping startups...")
    await scrape_yc_startups(1000)

    print("[6/7] Scraping products...")
    await scrape_products(1000)

    print("[7/7] Running entity resolution...")
    resolve_all_startups()

    print("\n=== Current counts ===")
    print(counts())

    print("\n=== Exporting to Google Sheets ===")
    export_all()

    print("\nPipeline complete.")


if __name__ == "__main__":
    asyncio.run(main())