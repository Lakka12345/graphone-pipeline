import asyncio
import aiohttp
import re
import logging
from dotenv import load_dotenv

from src.models.schemas import ProductRecord, ProductContent, Source
from src.storage.db import save_product, is_seen

load_dotenv()
logger = logging.getLogger(__name__)

README_URL = "https://raw.githubusercontent.com/mahseema/awesome-ai-tools/main/README.md"

# Additional awesome lists for more products
EXTRA_URLS = [
    "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md",
    "https://raw.githubusercontent.com/filipecalegario/awesome-generative-ai/main/README.md",
    "https://raw.githubusercontent.com/amusi/awesome-ai-awesomeness/master/README.md",
    "https://raw.githubusercontent.com/ikaijua/Awesome-AITools/main/README.md",
    "https://raw.githubusercontent.com/underlines/awesome-marketing-datascience/master/awesome-ai.md",
    "https://raw.githubusercontent.com/dariubs/GoBooks/master/README.md",
    "https://raw.githubusercontent.com/Shubhamsaboo/awesome-llm-apps/main/README.md",
    "https://raw.githubusercontent.com/tensorchord/awesome-llmops/main/README.md",
    "https://raw.githubusercontent.com/eugeneyan/open-llms/main/README.md",
    "https://raw.githubusercontent.com/brianspiering/awesome-dl4nlp/master/README.md",
    "https://raw.githubusercontent.com/kyrolabs/awesome-langchain/main/README.md",
    "https://raw.githubusercontent.com/continuedev/what-is-ai-coding/main/README.md",
    "https://raw.githubusercontent.com/eon01/awesome-chatgpt/master/README.md",
]

def detect_pricing(text: str) -> str | None:
    text = text.lower()
    if "freemium" in text:
        return "FREEMIUM"
    if "free" in text and not any(w in text for w in ["paid", "premium", "subscribe", "$"]):
        return "FREE"
    if "enterprise" in text:
        return "ENTERPRISE"
    if any(w in text for w in ["paid", "$", "per month", "pricing", "subscribe"]):
        return "PAID"
    return None


def parse_markdown_tools(markdown: str, source_name: str) -> list:
    """
    Parse markdown lines like:
    - [Product Name](https://url.com) - Description text
    """
    records = []
    # Match markdown links: - [Name](URL) - description
    pattern = re.compile(
        r"-\s+\[([^\]]+)\]\((https?://[^\)]+)\)\s*[-–:]?\s*(.*)"
    )

    for line in markdown.split("\n"):
        m = pattern.match(line.strip())
        if not m:
            continue

        name = m.group(1).strip()
        url = m.group(2).strip()
        description = m.group(3).strip()[:300]

        if not name or not url:
            continue
        if is_seen(url):
            continue

        pricing = detect_pricing(description)

        record = ProductRecord(
            source=Source(name=source_name, url=url),
            content=ProductContent(
                product_name=name,
                description=description or None,
                pricing_model=pricing,
                website=url,
            )
        )
        records.append(record)

    return records


async def fetch_markdown(session, url):
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Mozilla/5.0"}
        ) as r:
            if r.status == 200:
                return await r.text()
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return ""


async def scrape_products(target=1000):
    saved = 0
    all_urls = [README_URL] + EXTRA_URLS

    async with aiohttp.ClientSession() as session:
        for url in all_urls:
            if saved >= target:
                break

            print(f"  Fetching {url}...")
            markdown = await fetch_markdown(session, url)
            if not markdown:
                continue

            source_name = "awesome-ai-tools (GitHub)"
            records = parse_markdown_tools(markdown, source_name)
            print(f"  Found {len(records)} products in this list")

            for record in records:
                if saved >= target:
                    break
                save_product(record)
                saved += 1

            print(f"  Total saved so far: {saved}")

    print(f"\nProducts done. Total saved: {saved}")
    return saved


if __name__ == "__main__":
    asyncio.run(scrape_products(1000))