"""
Entity resolution — maps raw company names to canonical names.
Uses fuzzy matching against a seed list of known AI companies.
"""

from rapidfuzz import process, fuzz
from src.models.schemas import EntityMapping
from src.storage.db import save_entity_mapping

# Seed list of canonical AI company names
CANONICAL_ENTITIES = [
    "OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Mistral AI",
    "Cohere", "Hugging Face", "Stability AI", "Midjourney", "Runway",
    "Perplexity AI", "Character AI", "Inflection AI", "xAI", "Groq",
    "Together AI", "Replicate", "LangChain", "Pinecone", "Weaviate",
    "Qdrant", "Chroma", "Scale AI", "Weights & Biases", "MLflow",
    "Databricks", "Snowflake", "Palantir", "C3.ai", "DataRobot",
    "H2O.ai", "Dataiku", "Domino Data Lab", "Tecton", "Feast",
    "Nvidia", "AMD", "Intel", "Qualcomm", "Apple", "Microsoft",
    "Amazon", "Google", "IBM", "Salesforce", "Oracle", "SAP",
    "Zoom", "Slack", "Notion", "Airtable", "Monday.com", "Asana",
    "GitHub", "GitLab", "Atlassian", "JetBrains", "HashiCorp",
    "Cloudflare", "Fastly", "Vercel", "Netlify", "Supabase",
    "PlanetScale", "Neon", "CockroachDB", "MongoDB", "Redis",
    "Elastic", "Splunk", "Datadog", "New Relic", "Grafana",
    "Stripe", "Plaid", "Brex", "Ramp", "Mercury",
    "Figma", "Canva", "Adobe", "Autodesk", "Unity",
    "ElevenLabs", "Synthesia", "Descript", "Otter.ai", "AssemblyAI",
    "Whisper", "DeepL", "Grammarly", "Jasper", "Copy.ai",
    "Harvey", "Casetext", "Ironclad", "Veeva", "Tempus",
]

THRESHOLD = 85  # minimum fuzzy match score (0-100)


def normalize(name: str) -> str:
    """Lowercase, strip common suffixes."""
    name = name.lower().strip()
    for suffix in [" inc.", " inc", " ltd.", " ltd", " llc", " llc.",
                   " corp.", " corp", " ai", " technologies", " technology"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


def resolve(raw_name: str, entity_type: str, source_url: str) -> str:
    """
    Match raw_name to canonical entity.
    Returns canonical name if match found, else returns raw_name as-is.
    Saves mapping to DB.
    """
    if not raw_name:
        return raw_name

    # First try exact match (case insensitive)
    for canonical in CANONICAL_ENTITIES:
        if raw_name.lower() == canonical.lower():
            _save(raw_name, canonical, entity_type, source_url, 100.0)
            return canonical

    # Then fuzzy match on normalized names
    normalized_raw = normalize(raw_name)
    normalized_canonicals = {normalize(c): c for c in CANONICAL_ENTITIES}

    match = process.extractOne(
        normalized_raw,
        normalized_canonicals.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=THRESHOLD
    )

    if match:
        matched_normalized, score, _ = match
        canonical = normalized_canonicals[matched_normalized]
        _save(raw_name, canonical, entity_type, source_url, score)
        return canonical

    # No match — return as-is, still log it
    _save(raw_name, raw_name, entity_type, source_url, 0.0)
    return raw_name


def _save(raw_name, canonical_name, entity_type, source_url, confidence):
    if raw_name == canonical_name and confidence == 0.0:
        return  # don't log unmatched entries, keeps log clean
    mapping = EntityMapping(
        raw_name=raw_name,
        canonical_name=canonical_name,
        entity_type=entity_type,
        source_url=source_url,
        confidence=confidence,
    )
    save_entity_mapping(mapping)


def resolve_all_startups():
    """Run entity resolution on all saved startups."""
    import sqlite3, json
    from pathlib import Path

    conn = sqlite3.connect("data/pipeline.db")
    rows = conn.execute("SELECT record_id, data FROM startups").fetchall()
    resolved = 0

    for record_id, data_json in rows:
        data = json.loads(data_json)
        raw_name = data["content"]["entity_name"]
        source_url = data["source"]["url"]
        canonical = resolve(raw_name, "STARTUP", source_url)

        if canonical != raw_name:
            conn.execute(
                "UPDATE startups SET canonical_entity=? WHERE record_id=?",
                (canonical, record_id)
            )
            resolved += 1

    conn.commit()
    conn.close()
    print(f"Entity resolution done. {resolved} startups matched to canonical names.")
    return resolved



def resolve_all_products():
    """Run entity resolution on all saved products."""
    import sqlite3, json
    from src.models.schemas import EntityMapping
    from datetime import datetime

    conn = sqlite3.connect("data/pipeline.db")
    rows = conn.execute("SELECT record_id, data FROM products").fetchall()
    resolved = 0

    for record_id, data_json in rows:
        data = json.loads(data_json)
        raw_name = data["content"].get("startup_name") or data["content"].get("product_name")
        source_url = data["source"]["url"]

        if not raw_name:
            continue

        # Normalize and fuzzy match
        normalized_raw = normalize(raw_name)
        normalized_canonicals = {normalize(c): c for c in CANONICAL_ENTITIES}

        # Exact match first
        canonical = raw_name
        confidence = 0.0
        for c in CANONICAL_ENTITIES:
            if raw_name.lower() == c.lower():
                canonical = c
                confidence = 100.0
                break

        # Fuzzy match if no exact
        if confidence == 0.0:
            match = process.extractOne(
                normalized_raw,
                normalized_canonicals.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=THRESHOLD
            )
            if match:
                matched_normalized, score, _ = match
                canonical = normalized_canonicals[matched_normalized]
                confidence = score

        if canonical != raw_name and confidence > 0:
            conn.execute(
                "UPDATE products SET canonical_entity=? WHERE record_id=?",
                (canonical, record_id)
            )
            conn.execute(
                "INSERT OR REPLACE INTO entity_mappings VALUES (?,?,?,?,?,?)",
                (raw_name, canonical, "PRODUCT", source_url,
                 confidence, datetime.utcnow().isoformat())
            )
            resolved += 1

    conn.commit()
    conn.close()
    print(f"Product entity resolution done. {resolved} products matched to canonical names.")
    return resolved

if __name__ == "__main__":
    resolve_all_startups()
    resolve_all_products()