"""
Export all data from SQLite to Google Sheets.
One function per tab.
"""

import json
import gspread
from google.oauth2.service_account import Credentials
from src.storage.db import fetch_all, fetch_entity_mappings
import os
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "")


def get_sheet():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)


def clear_and_write(worksheet, headers, rows):
    """Clear sheet, write headers, write rows in batches."""
    worksheet.clear()
    all_data = [headers] + rows
    # Write in batches of 500 to avoid API limits
    for i in range(0, len(all_data), 500):
        worksheet.append_rows(all_data[i:i+500])
    print(f"  Written {len(rows)} rows to {worksheet.title}")


def export_startups(sheet):
    print("Exporting startups...")
    records = fetch_all("startups")
    headers = ["entity_name", "description", "founded_year", "employee_count",
               "funding_total", "location", "website", "source_url", "canonical_entity", "collected_at"]
    rows = []
    for r in records:
        c = r["content"]
        rows.append([
            c.get("entity_name", ""),
            c.get("description", ""),
            c.get("founded_year", ""),
            c.get("employee_count", ""),
            c.get("funding_total", ""),
            c.get("location", ""),
            c.get("website", ""),
            r["source"]["url"],
            r.get("canonical_entity", ""),
            r.get("collected_at", ""),
        ])
    clear_and_write(sheet.worksheet("Startups"), headers, rows)


def export_products(sheet):
    print("Exporting products...")
    records = fetch_all("products")
    headers = ["product_name", "startup_name", "description", "pricing_model",
               "website", "source_url", "collected_at"]
    rows = []
    for r in records:
        c = r["content"]
        rows.append([
            c.get("product_name", ""),
            c.get("startup_name", ""),
            c.get("description", ""),
            c.get("pricing_model", ""),
            c.get("website", ""),
            r["source"]["url"],
            r.get("collected_at", ""),
        ])
    clear_and_write(sheet.worksheet("Products"), headers, rows)


def export_papers(sheet):
    print("Exporting papers...")
    records = fetch_all("papers")
    headers = ["title", "authors", "published_date", "paper_url",
               "github_url", "github_stars", "source_url", "collected_at"]
    rows = []
    for r in records:
        c = r["content"]
        rows.append([
            c.get("title", ""),
            ", ".join(c.get("authors", [])),
            c.get("published_date", ""),
            c.get("paper_url", ""),
            c.get("github_url", ""),
            c.get("github_stars", ""),
            r["source"]["url"],
            r.get("collected_at", ""),
        ])
    clear_and_write(sheet.worksheet("Papers"), headers, rows)


def export_news(sheet):
    print("Exporting news...")
    records = fetch_all("news")
    headers = ["title", "summary", "author", "published_at",
               "article_url", "source_name", "collected_at"]
    rows = []
    for r in records:
        c = r["content"]
        rows.append([
            c.get("title", ""),
            c.get("summary", ""),
            c.get("author", ""),
            c.get("published_at", ""),
            c.get("article_url", ""),
            r["source"]["name"],
            r.get("collected_at", ""),
        ])
    clear_and_write(sheet.worksheet("News"), headers, rows)


def export_jobs(sheet):
    print("Exporting jobs...")
    records = fetch_all("jobs")
    headers = ["title", "company", "location", "remote",
               "description", "posted_at", "job_url", "source_name", "collected_at"]
    rows = []
    for r in records:
        c = r["content"]
        rows.append([
            c.get("title", ""),
            c.get("company", ""),
            c.get("location", ""),
            c.get("remote", ""),
            c.get("description", ""),
            c.get("posted_at", ""),
            c.get("job_url", ""),
            r["source"]["name"],
            r.get("collected_at", ""),
        ])
    clear_and_write(sheet.worksheet("Jobs"), headers, rows)


def export_entity_mappings(sheet):
    print("Exporting entity mappings...")
    records = fetch_entity_mappings()
    headers = ["raw_name", "canonical_name", "entity_type",
               "source_url", "confidence", "resolved_at"]
    rows = []
    for r in records:
        rows.append([
            r.get("raw_name", ""),
            r.get("canonical_name", ""),
            r.get("entity_type", ""),
            r.get("source_url", ""),
            r.get("confidence", ""),
            r.get("resolved_at", ""),
        ])
    clear_and_write(sheet.worksheet("Entity Mapping Log"), headers, rows)


def export_all():
    print("Connecting to Google Sheets...")
    sheet = get_sheet()
    export_startups(sheet)
    export_products(sheet)
    export_papers(sheet)
    export_news(sheet)
    export_jobs(sheet)
    export_entity_mappings(sheet)
    print("\nAll done! Check your Google Sheet.")


if __name__ == "__main__":
    export_all()