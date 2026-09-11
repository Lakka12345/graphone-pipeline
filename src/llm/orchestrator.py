import os
import json
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def extract_with_groq(text: str, prompt: str) -> dict | None:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:6000]}
            ],
            temperature=0,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        return parse_json(raw)
    except Exception as e:
        logger.warning(f"Groq failed: {e}")
        return None


def extract_with_gemini(text: str, prompt: str) -> dict | None:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"{prompt}\n\nText:\n{text[:6000]}"
        )
        raw = response.text.strip()
        return parse_json(raw)
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")
        return None


def extract_with_deepseek(text: str, prompt: str) -> dict | None:
    """DeepSeek via OpenAI-compatible API."""
    try:
        import httpx
        response = httpx.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY', '')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text[:6000]}
                ],
                "temperature": 0,
                "max_tokens": 1000,
            },
            timeout=30
        )
        raw = response.json()["choices"][0]["message"]["content"].strip()
        return parse_json(raw)
    except Exception as e:
        logger.warning(f"DeepSeek failed: {e}")
        return None


def parse_json(raw: str) -> dict | None:
    """Extract JSON from LLM response, handles markdown code blocks."""
    try:
        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return None


def extract(text: str, prompt: str, max_retries: int = 2) -> dict | None:
    """
    Main extraction function with fallback chain.
    Groq → Gemini → DeepSeek
    Retries with exponential backoff on rate limits.
    """
    providers = [
        ("Groq", extract_with_groq),
        ("Gemini", extract_with_gemini),
        ("DeepSeek", extract_with_deepseek),
    ]

    for provider_name, provider_fn in providers:
        for attempt in range(max_retries):
            result = provider_fn(text, prompt)
            if result:
                logger.info(f"Extracted with {provider_name}")
                return result
            # Exponential backoff before retry
            wait = 2 ** attempt
            logger.warning(f"{provider_name} attempt {attempt+1} failed, waiting {wait}s")
            time.sleep(wait)

    logger.error("All providers failed")
    return None


# ── Prompts ────────────────────────────────────────────────────────────────────

STARTUP_PROMPT = """
You are a data extraction assistant. Extract startup information from the text below.
Return ONLY a JSON object with these fields:
{
  "entity_name": "company name or null",
  "description": "one line description or null",
  "founded_year": number or null,
  "employee_count": number or null,
  "funding_total": "e.g. $10M or null",
  "location": "city, country or null",
  "website": "url or null"
}
IMPORTANT: Only extract information explicitly stated in the text. Use null for anything not mentioned.
Do NOT guess or infer values.
"""

PRODUCT_PROMPT = """
You are a data extraction assistant. Extract AI product information from the text below.
Return ONLY a JSON object with these fields:
{
  "product_name": "product name or null",
  "startup_name": "company name or null",
  "description": "one line description or null",
  "pricing_model": "FREE or FREEMIUM or PAID or ENTERPRISE or null"
}
IMPORTANT: Only extract information explicitly stated in the text.
For pricing_model, only use one of the four values above. Use null if pricing is not mentioned.
Do NOT guess.
"""