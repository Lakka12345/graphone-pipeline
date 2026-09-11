import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

DB_PATH = Path("data/pipeline.db")

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS startups (
            record_id TEXT PRIMARY KEY,
            entity_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            data JSON NOT NULL,
            collected_at TEXT,
            canonical_entity TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            record_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            data JSON NOT NULL,
            collected_at TEXT,
            canonical_entity TEXT
        );

        CREATE TABLE IF NOT EXISTS papers (
            record_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            paper_url TEXT NOT NULL UNIQUE,
            data JSON NOT NULL,
            collected_at TEXT
        );

        CREATE TABLE IF NOT EXISTS news (
            record_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            article_url TEXT NOT NULL UNIQUE,
            source_name TEXT,
            published_at TEXT,
            data JSON NOT NULL,
            collected_at TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            record_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            job_url TEXT NOT NULL UNIQUE,
            company TEXT,
            posted_at TEXT,
            data JSON NOT NULL,
            collected_at TEXT
        );

        CREATE TABLE IF NOT EXISTS entity_mappings (
            raw_name TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            entity_type TEXT,
            source_url TEXT,
            confidence REAL,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS seen_urls (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            first_seen TEXT
        );
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def is_seen(url: str) -> bool:
    """Returns True if URL already processed. Marks it as seen if not."""
    h = hashlib.sha256(url.strip().lower().encode()).hexdigest()
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM seen_urls WHERE url_hash=?", (h,)).fetchone()
        if row:
            return True
        conn.execute(
            "INSERT OR IGNORE INTO seen_urls VALUES (?,?,?)",
            (h, url, datetime.utcnow().isoformat())
        )
        return False

def save_startup(record):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO startups VALUES (?,?,?,?,?,?)",
            (record.record_id, record.content.entity_name,
             record.source.url, record.model_dump_json(),
             record.collected_at.isoformat(), record.canonical_entity)
        )

def save_product(record):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?)",
            (record.record_id, record.content.product_name,
             record.source.url, record.model_dump_json(),
             record.collected_at.isoformat(), record.canonical_entity)
        )

def save_paper(record):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO papers VALUES (?,?,?,?,?)",
            (record.record_id, record.content.title,
             record.content.paper_url, record.model_dump_json(),
             record.collected_at.isoformat())
        )

def save_news(record):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO news VALUES (?,?,?,?,?,?,?)",
            (record.record_id, record.content.title,
             record.content.article_url, record.source.name,
             record.content.published_at.isoformat() if record.content.published_at else None,
             record.model_dump_json(), record.collected_at.isoformat())
        )

def save_job(record):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?,?)",
            (record.record_id, record.content.title,
             record.content.job_url, record.content.company,
             record.content.posted_at.isoformat() if record.content.posted_at else None,
             record.model_dump_json(), record.collected_at.isoformat())
        )

def save_entity_mapping(mapping):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO entity_mappings VALUES (?,?,?,?,?,?)",
            (mapping.raw_name, mapping.canonical_name, mapping.entity_type,
             mapping.source_url, mapping.confidence,
             mapping.resolved_at.isoformat())
        )

def fetch_all(table: str):
    with get_conn() as conn:
        rows = conn.execute(f"SELECT data FROM {table}").fetchall()
        return [json.loads(r["data"]) for r in rows]

def fetch_entity_mappings():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM entity_mappings").fetchall()
        return [dict(r) for r in rows]

def counts():
    tables = ["startups", "products", "papers", "news", "jobs", "entity_mappings"]
    with get_conn() as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}